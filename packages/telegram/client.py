"""
packages/telegram/client.py
────────────────────────────
Инициализация Telethon клиента с StringSession.

Возможности:
  - Singleton паттерн: один клиент на всё приложение
  - Загрузка зашифрованной StringSession из файла
  - Авторизация если сессия не найдена

Использование:
    from packages.telegram.client import get_client

    client = await get_client()
"""

import logging
import os
from typing import Optional

from telethon import TelegramClient
from telethon.sessions import StringSession

from packages.config.settings import settings
from packages.cli.session_manager import session_manager

logger = logging.getLogger(__name__)

_client_instance: Optional[TelegramClient] = None


async def get_client() -> TelegramClient:
    """
    Возвращает (создаёт) единственный экземпляр TelegramClient.
    
    При первом вызове:
    1. Пытается загрузить зашифрованную StringSession из файла
    2. Если файл есть — использует его
    3. Если нет — создаёт клиент без сессии (onboarding авторизует)

    :return: Подключённый TelegramClient
    """
    global _client_instance

    if _client_instance is not None and _client_instance.is_connected():
        return _client_instance

    # Пытаемся загрузить сохранённую сессию
    session_string = session_manager.load_session()

    if session_string:
        logger.info("[Client] Загружена сохранённая сессия")
        session = StringSession(session_string)
    else:
        logger.info("[Client] Сессия не найдена, создаём новую")
        session = StringSession()

    _client_instance = TelegramClient(
        session=session,
        api_id=settings.api_id,
        api_hash=settings.api_hash,
        # Параметры для снижения риска бана:
        device_model="iPhone 15 Pro",
        system_version="iOS 17.4.1",
        app_version="10.2.3",
        lang_code="ru",
        system_lang_code="ru-RU",
    )

    await _client_instance.connect()

    if not await _client_instance.is_user_authorized():
        logger.warning("[Client] Пользователь не авторизован. Запустите onboarding.")

    return _client_instance


def reset_client() -> None:
    """Сбрасывает синглтон (для тестов)."""
    global _client_instance
    _client_instance = None
