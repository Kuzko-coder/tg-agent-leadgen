"""
packages/database/repository.py
──────────────────────────────────
Async CRUD операции для SQLite через aiosqlite.

Основные функции:
  - init_db()               : создать таблицы (вызывается при старте)
  - get_history(chat_id)    : последние 10 сообщений диалога
  - append_message(...)     : сохранить сообщение (user или assistant)
  - prune_old_dialogs(days) : удалить записи старше N дней
  - upsert_lead(...)        : создать или обновить лида
  - get_lead(chat_id)       : получить лида по chat_id
  - advance_lead_step(...)  : продвинуть лида по воронке OARS
  - get_stats()             : статистика для report_job
"""

import aiosqlite
import time
from typing import Optional, List, Dict, Any

from packages.config.settings import settings
from packages.database.models import ALL_MIGRATIONS

# ─── Порядок состояний воронки ─────────────────────────────────────────────
LEAD_STATES = ["NEW", "ENGAGED", "WARM", "CONVERTED"]


async def init_db() -> None:
    """
    Запускает все SQL-миграции.
    Вызывается один раз при старте main.py.
    """
    async with aiosqlite.connect(settings.db_path) as db:
        # Включаем WAL-режим для concurrent read/write без блокировок
        await db.execute("PRAGMA journal_mode=WAL;")
        for migration in ALL_MIGRATIONS:
            await db.execute(migration)
        await db.commit()


async def get_history(chat_id: int, limit: int = 10) -> List[Dict[str, str]]:
    """
    Возвращает последние `limit` сообщений для данного chat_id
    в формате, совместимом с OpenAI messages API:
    [{"role": "user", "content": "..."}, ...]
    """
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT role, content FROM dialogs
            WHERE chat_id = ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (chat_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [{"role": r["role"], "content": r["content"]} for r in rows]


async def append_message(chat_id: int, role: str, content: str) -> None:
    """
    Добавляет сообщение в историю диалога.
    После вставки автоматически оставляет только последние 10 записей,
    удаляя самые старые (скользящее окно).

    :param chat_id: Telegram chat ID
    :param role: "user" или "assistant"
    :param content: Текст сообщения
    """
    async with aiosqlite.connect(settings.db_path) as db:
        # Вставляем новое сообщение
        await db.execute(
            "INSERT INTO dialogs (chat_id, role, content) VALUES (?, ?, ?)",
            (chat_id, role, content),
        )
        # Удаляем всё лишнее (оставляем только 10 последних)
        await db.execute(
            """
            DELETE FROM dialogs WHERE id IN (
                SELECT id FROM dialogs
                WHERE chat_id = ?
                ORDER BY created_at DESC
                LIMIT -1 OFFSET 10
            )
            """,
            (chat_id,),
        )
        await db.commit()


async def prune_old_dialogs(days: int) -> int:
    """
    Удаляет записи диалогов старше `days` дней.
    Используется cleanup_job.

    :return: Количество удалённых строк
    """
    cutoff = time.time() - days * 86400
    async with aiosqlite.connect(settings.db_path) as db:
        cursor = await db.execute(
            "DELETE FROM dialogs WHERE created_at < ?", (cutoff,)
        )
        await db.commit()
        return cursor.rowcount


async def upsert_lead(
    chat_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
) -> None:
    """
    Создаёт нового лида или обновляет last_activity_at для существующего.
    При первом создании — state = 'NEW', oars_step = 1.
    """
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            """
            INSERT INTO leads (chat_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                last_activity_at = unixepoch('now'),
                username = COALESCE(excluded.username, leads.username),
                first_name = COALESCE(excluded.first_name, leads.first_name)
            """,
            (chat_id, username, first_name),
        )
        await db.commit()


async def get_lead(chat_id: int) -> Optional[Dict[str, Any]]:
    """
    Возвращает словарь с данными лида или None если не найден.
    """
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM leads WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def advance_lead_step(chat_id: int) -> str:
    """
    Продвигает лида на следующий шаг OARS.
    NEW → ENGAGED → WARM → CONVERTED.

    :return: Новое состояние лида
    """
    lead = await get_lead(chat_id)
    if not lead:
        return "NEW"

    current_step = lead["oars_step"]
    current_state = lead["state"]

    new_step = min(current_step + 1, 4)

    # Маппинг шага → состояние воронки
    step_to_state = {1: "NEW", 2: "ENGAGED", 3: "WARM", 4: "CONVERTED"}
    new_state = step_to_state.get(new_step, current_state)

    converted_at_sql = "unixepoch('now')" if new_state == "CONVERTED" else "leads.converted_at"

    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            f"""
            UPDATE leads SET
                oars_step = ?,
                state = ?,
                last_activity_at = unixepoch('now'),
                converted_at = {converted_at_sql}
            WHERE chat_id = ?
            """,
            (new_step, new_state, chat_id),
        )
        await db.commit()

    return new_state


async def get_stats() -> Dict[str, Any]:
    """
    Возвращает статистику для ежедневного отчёта:
    - total_leads: всего лидов
    - new_today: новых за сегодня
    - converted_total: всего конвертировано
    - converted_today: конвертировано за сегодня
    - by_state: разбивка по состояниям
    """
    today_start = time.time() - 86400  # последние 24 часа

    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute("SELECT COUNT(*) as cnt FROM leads") as c:
            total_leads = (await c.fetchone())["cnt"]

        async with db.execute(
            "SELECT COUNT(*) as cnt FROM leads WHERE triggered_at > ?", (today_start,)
        ) as c:
            new_today = (await c.fetchone())["cnt"]

        async with db.execute(
            "SELECT COUNT(*) as cnt FROM leads WHERE state = 'CONVERTED'"
        ) as c:
            converted_total = (await c.fetchone())["cnt"]

        async with db.execute(
            "SELECT COUNT(*) as cnt FROM leads WHERE converted_at > ?", (today_start,)
        ) as c:
            converted_today = (await c.fetchone())["cnt"]

        async with db.execute(
            "SELECT state, COUNT(*) as cnt FROM leads GROUP BY state"
        ) as c:
            rows = await c.fetchall()
            by_state = {r["state"]: r["cnt"] for r in rows}

    return {
        "total_leads": total_leads,
        "new_today": new_today,
        "converted_total": converted_total,
        "converted_today": converted_today,
        "by_state": by_state,
    }


async def get_leads(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Возвращает список лидов для веб-дашборда.
    Сортировка: сначала самые новые активные.
    """
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT
                chat_id, username, first_name, state, oars_step,
                triggered_at, last_activity_at, converted_at,
                datetime(triggered_at, 'unixepoch') as created_at
            FROM leads
            ORDER BY last_activity_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
