"""
packages/memory/dialog_memory.py
──────────────────────────────────
In-memory кэш истории диалогов с персистентностью через SQLite.

Хранит последние 10 сообщений для каждого chat_id в RAM (dict).
При запросе chat_id, которого ещё нет в кэше — загружает из БД.
После каждого нового сообщения — сохраняет в БД (async).

Использование:
    from packages.memory.dialog_memory import dialog_memory

    history = await dialog_memory.get(chat_id)
    await dialog_memory.add(chat_id, role="user", content="Привет!")
"""

import asyncio
from collections import defaultdict, deque
from typing import List, Dict, Deque

from packages.database import repository

# Максимальное количество сообщений в памяти на один чат
MAX_MESSAGES = 10


class DialogMemory:
    """
    Потокобезопасный (asyncio) менеджер истории диалогов.
    
    Внутри хранит deque(maxlen=10) для каждого chat_id.
    При первом обращении к новому chat_id — прогревает кэш из БД.
    """

    def __init__(self):
        # chat_id -> deque of {"role": ..., "content": ...}
        self._cache: Dict[int, Deque[Dict[str, str]]] = defaultdict(
            lambda: deque(maxlen=MAX_MESSAGES)
        )
        # Флаги прогрева: chat_id -> True если уже загружено из БД
        self._warmed: Dict[int, bool] = {}
        # Блокировка для безопасной инициализации кэша
        self._lock = asyncio.Lock()

    async def _warm_up(self, chat_id: int) -> None:
        """
        Загружает историю из БД в RAM при первом обращении к chat_id.
        Использует блокировку во избежание двойной загрузки.
        """
        async with self._lock:
            if self._warmed.get(chat_id):
                return
            rows = await repository.get_history(chat_id, limit=MAX_MESSAGES)
            for row in rows:
                self._cache[chat_id].append(row)
            self._warmed[chat_id] = True

    async def get(self, chat_id: int) -> List[Dict[str, str]]:
        """
        Возвращает список сообщений для chat_id в формате OpenAI messages.
        [{"role": "user", "content": "..."}, ...]
        """
        if not self._warmed.get(chat_id):
            await self._warm_up(chat_id)
        return list(self._cache[chat_id])

    async def add(self, chat_id: int, role: str, content: str) -> None:
        """
        Добавляет сообщение в кэш И персистирует в SQLite.
        
        :param chat_id: Telegram chat ID
        :param role: "user" или "assistant"
        :param content: Текст сообщения
        """
        if not self._warmed.get(chat_id):
            await self._warm_up(chat_id)

        msg = {"role": role, "content": content}
        self._cache[chat_id].append(msg)  # deque автоматически выталкивает старые

        # Персистируем в БД (не блокирует основной поток)
        await repository.append_message(chat_id, role, content)

    def clear(self, chat_id: int) -> None:
        """Сбрасывает кэш для конкретного чата (без удаления из БД)."""
        self._cache[chat_id].clear()
        self._warmed[chat_id] = False

    def get_message_count(self, chat_id: int) -> int:
        """Возвращает текущее количество сообщений в кэше."""
        return len(self._cache[chat_id])


# Синглтон - используется напрямую как `from packages.memory.dialog_memory import dialog_memory`
dialog_memory = DialogMemory()
