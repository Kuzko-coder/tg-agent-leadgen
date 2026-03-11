"""
packages/jobs/report_job.py
────────────────────────────
Фоновый job: ежедневный отчёт о работе агента.

Выводит статистику:
  - Новых лидов за 24ч
  - Конверсий за 24ч
  - Всего лидов и конверсий
  - Разбивка по состояниям воронки

Отправляет в:
  1. Консоль (всегда)
  2. Telegram ЛС пользователю (если настроен REPORT_RECIPIENT_ID)

Использование:
    from packages.jobs.report_job import start_report_job

    asyncio.create_task(start_report_job(client))
"""

import asyncio
import logging
from typing import Optional

from telethon import TelegramClient

from packages.config.settings import settings
from packages.database import repository
from packages.core.anti_ban import safe_call

logger = logging.getLogger(__name__)


def _format_report(stats: dict) -> str:
    """Форматирует статистику в читаемый текстовый отчёт."""
    by_state = stats.get("by_state", {})
    state_lines = "\n".join(
        f"  • {state}: {count}" for state, count in by_state.items()
    )

    return (
        f"📊 Ежедневный отчёт агента\n"
        f"{'─' * 30}\n"
        f"👥 Новых лидов за 24ч: {stats['new_today']}\n"
        f"🎯 Конверсий за 24ч: {stats['converted_today']}\n"
        f"\n"
        f"📈 Всего лидов: {stats['total_leads']}\n"
        f"✅ Всего конверсий: {stats['converted_total']}\n"
        f"\n"
        f"Воронка по состояниям:\n"
        f"{state_lines or '  (нет данных)'}\n"
        f"{'─' * 30}"
    )


async def start_report_job(client: Optional[TelegramClient] = None) -> None:
    """
    Бесконечный цикл генерации отчётов.
    Запускать как asyncio.Task при старте приложения.

    :param client: TelegramClient для отправки отчёта в ЛС (опционально)
    """
    interval_seconds = settings.report_interval_hours * 3600
    recipient_id = settings.report_recipient_id

    logger.info(
        f"[ReportJob] Запущен. Интервал: {settings.report_interval_hours}ч. "
        f"Получатель: {recipient_id or 'только консоль'}"
    )

    while True:
        try:
            # Ждём до следующего отчёта
            await asyncio.sleep(interval_seconds)

            # Собираем статистику из БД
            stats = await repository.get_stats()
            report_text = _format_report(stats)

            # 1. Всегда выводим в консоль
            logger.info(f"[ReportJob]\n{report_text}")

            # 2. Отправляем в Telegram ЛС если настроен получатель
            if client and recipient_id and recipient_id > 0:
                await safe_call(
                    client.send_message,
                    recipient_id,
                    report_text,
                )
                logger.info(f"[ReportJob] Отчёт отправлен пользователю {recipient_id}")

        except asyncio.CancelledError:
            logger.info("[ReportJob] Остановлен")
            break
        except Exception as e:
            logger.error(f"[ReportJob] Ошибка: {e}", exc_info=True)
            await asyncio.sleep(300)  # 5 минут перед retry
