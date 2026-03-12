"""
packages/telegram/handlers.py
───────────────────────────────
Обработчики событий Telegram.

Регистрирует хэндлер на входящие сообщения (events.NewMessage).
Фильтрует сообщения:
  - Игнорирует: self, бота, служебные сервисы, пустые тексты
  - Публичные чаты: проверяет триггер-слова → очередь
  - Личные чаты: если диалог уже активен (follow-up в ЛС) → очередь

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
            # 1. Игнорируем свои исходящие сообщения
            if event.out:
                return

            # 2. Игнорируем пустые сообщения (медиа без подписи и т.п.)
            if not event.message or not event.message.text:
                return

            # 3. Получаем отправителя — нужен для фильтрации ботов
            sender = await event.get_sender()
            if not sender:
                return

            # 4. Игнорируем ботов и сервисные аккаунты Telegram
            if getattr(sender, "bot", False):
                return
            if getattr(sender, "support", False):
                return
            # Telegram Service Notifications (системные уведомления)
            if getattr(sender, "id", None) in (777000, 42777):
                return

            text = event.message.text
            chat_id = event.chat_id
            is_private = event.is_private

            # BUG FIX: агент должен мониторить ПУБЛИЧНЫЕ чаты ─ это главная функция.
            # Логика: публичный чат → только при триггере (первый выстрел).
            #         личный чат    → если диалог уже был начат в публичном чате.
            # УБИРАЕМ РАННИЙ ВЫХОД event.is_private — он блокировал все группы!

            # 5. Проверяем триггер-слова (с учётом first-shot rule)
            if not trigger_filter.should_process(chat_id, text):
                # В личке разрешаем если диалог активен (follow-up)
                if not (is_private and trigger_filter.is_active(chat_id)):
                    return

            # 6. Кладём в очередь агента
            logger.info(
                f"[Handler] Триггер сработал! chat_id={chat_id} "
                f"от @{getattr(sender, 'username', 'unknown')} "
                f"({'private' if is_private else 'group'})"
            )
            await queue.put(event)

        except Exception as e:
            logger.error(f"[Handler] Ошибка в on_new_message: {e}", exc_info=True)

    logger.info("[Handler] Обработчик NewMessage зарегистрирован")
