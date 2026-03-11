"""
packages/agent/trigger_filter.py
──────────────────────────────────
Фильтр триггер-слов с реализацией правила «Первого выстрела».

Правило «Первого выстрела»:
  Обрабатывать только первое найденное триггер-слово в данном чате.
  Если chat_id уже в triggered_chats → игнорировать все последующие триггеры.
  Это предотвращает спам и банны.

Использование:
    from packages.agent.trigger_filter import trigger_filter

    if trigger_filter.should_process(chat_id, text):
        ...
"""

import logging
from typing import Set

from packages.config.settings import settings

logger = logging.getLogger(__name__)


class TriggerFilter:
    """
    Фильтр входящих сообщений по триггер-словам.

    Состояние:
      _triggered_chats: Set[int] — chat_id которые уже были обработаны
                                   (first-shot rule: только одно срабатывание)
    """

    def __init__(self):
        # Множество chat_id, в которых агент уже начал диалог
        self._triggered_chats: Set[int] = set()

    def _contains_trigger(self, text: str) -> bool:
        """
        Проверяет, содержит ли текст хотя бы одно триггер-слово.
        Поиск регистронезависимый.
        """
        text_lower = text.lower()
        for word in settings.trigger_words:
            if word in text_lower:
                logger.debug(f"[TriggerFilter] Найдено триггер-слово: '{word}'")
                return True
        return False

    def should_process(self, chat_id: int, text: str) -> bool:
        """
        Определяет, нужно ли обрабатывать сообщение.

        Правила:
        1. Если chat_id уже в triggered_chats — пропускаем ВСЕ триггеры
           (диалог уже идёт → агент отвечает на всё входящее)
        2. Если chat_id новый → проверяем триггер-слова
        3. Нашли триггер → добавляем в tracked, разрешаем обработку

        :param chat_id: Telegram chat ID
        :param text: Текст входящего сообщения
        :return: True если нужно передать агенту
        """
        # Если диалог уже активен — агент должен отвечать на все сообщения
        if chat_id in self._triggered_chats:
            logger.debug(f"[TriggerFilter] chat_id={chat_id} активен, передаю в агента")
            return True

        # Новый чат — проверяем наличие триггера
        if self._contains_trigger(text):
            self._triggered_chats.add(chat_id)
            logger.info(
                f"[TriggerFilter] Новый лид! chat_id={chat_id}. "
                f"Всего активных: {len(self._triggered_chats)}"
            )
            return True

        # Нет триггера → игнорируем
        return False

    def release(self, chat_id: int) -> None:
        """
        Освобождает чат из tracked (например, после конверсии или по таймауту).
        """
        self._triggered_chats.discard(chat_id)
        logger.info(f"[TriggerFilter] chat_id={chat_id} удалён из активных")

    def get_active_count(self) -> int:
        """Возвращает количество активных диалогов."""
        return len(self._triggered_chats)

    def is_active(self, chat_id: int) -> bool:
        """Проверяет, активен ли диалог в данном чате."""
        return chat_id in self._triggered_chats


# Синглтон
trigger_filter = TriggerFilter()
