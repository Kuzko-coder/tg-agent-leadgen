"""
packages/telegram/handlers.py
───────────────────────────────
Обработчики событий Telegram.

Регистрирует хэндлер на входящие сообщения (events.NewMessage).
Фильтрует сообщения:
  - Игнорирует: self, бота, служебные сервисы
  - Пропускает только: личные чаты (private) с триггер-словами

При совпадении — кладёт событие в asyncio.Queue для обработки агентом.

Использование:
    from packages.telegram.handlers import register_handlers

    register_handlers(client, queue)
"""

import asyncio
import logging

from telethon import TelegramClient, events

from packages.agent.trigger_filter import trigger_filter

logger = logging.getLogger(__name__)


def register_handlers(client: TelegramClient, queue: asyncio.Queue) -> None:
    """
    Регистрирует обработчики событий на клиенте Telethon.
    
    :param client: Инициализированный TelegramClient
    :param queue: asyncio.Queue для передачи событий в агента
    """

    @client.on(events.NewMessage(incoming=True))
    async def on_new_message(event: events.NewMessage.Event) -> None:
        """
        Обработчик входящих сообщений.
        
        Порядок фильтрации (от дешёвого к дорогому):
        1. Игнор: из себя (me)
        2. Игнор: нет текста
        3. Игнор: не личный чат (только private DM)
        4. Игнор: боты и сервисные аккаунты
        5. Триггер-фильтр: есть ли ключевое слово в тексте?
        6. Если прошло — в очередь
        """
        try:
            # 1. Игнорируем свои сообщения
            if event.out:
                return

            # 2. Игнорируем пустые сообщения
            if not event.message or not event.message.text:
                return

            # 3. Только личные чаты (private DM)
            if not event.is_private:
                return

            # 4. Игнорируем ботов и сервисные аккаунты
            sender = await event.get_sender()
            if not sender:
                return
            if getattr(sender, "bot", False):
                return
            if getattr(sender, "support", False):
                return
            # Telegram Services (системные аккаунты с id < 0 или спецID)
            if sender.id in (777000, 42777):  # Telegram Service Notifications
                return

            text = event.message.text
            chat_id = event.chat_id

            # 5. Проверяем триггер-слова (с учётом first-shot rule)
            if not trigger_filter.should_process(chat_id, text):
                return

            # 6. Кладём в очередь агента
            logger.info(
                f"[Handler] Триггер сработал! chat_id={chat_id} "
                f"от @{getattr(sender, 'username', 'unknown')}"
            )
            await queue.put(event)

        except Exception as e:
            logger.error(f"[Handler] Ошибка в on_new_message: {e}", exc_info=True)

    logger.info("[Handler] Обработчик NewMessage зарегистрирован")
