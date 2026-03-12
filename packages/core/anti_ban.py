"""
packages/core/anti_ban.py
──────────────────────────
Защита от банов Telegram.

Обработчики ошибок:
  - FloodWaitError   : автоматически спим столько, сколько просит Telegram + 5с
  - SlowModeWaitError: аналогично для chats с slow mode
  - Exponential backoff для сетевых ошибок

Использование:
    from packages.core.anti_ban import safe_call

    result = await safe_call(client.send_message, chat_id, text)
"""

import asyncio
import logging
import functools
from typing import Callable, Any

from telethon.errors import (
    FloodWaitError,
    SlowModeWaitError,
    UserBannedInChannelError,
    ChatWriteForbiddenError,
    PeerFloodError,
)

logger = logging.getLogger(__name__)

# Максимальное количество retry для сетевых ошибок
MAX_NETWORK_RETRIES = 3
# Максимальное количество retry при FloodWait/PeerFlood (защита от бана)
# BUG FIX: раньше continue в FloodWait вел к бесконечному циклу
MAX_FLOOD_RETRIES = 5
# Базовая задержка для exponential backoff (секунды)
BASE_BACKOFF = 2.0


async def safe_call(coro_func: Callable, *args, **kwargs) -> Any:
    """
    Оборачивает любой вызов Telethon API в anti-ban защиту.

    При FloodWaitError — ждёт ровно столько, сколько требует Telegram.
    При сетевых ошибках — exponential backoff (2, 4, 8 секунд).
    BUG FIX: добавлен лимит MAX_FLOOD_RETRIES чтобы FloodWait/PeerFlood
             не приводил к бесконечному циклу.

    Использование:
        result = await safe_call(client.send_message, chat_id, text)
    """
    flood_attempts = 0

    for attempt in range(MAX_NETWORK_RETRIES):
        try:
            return await coro_func(*args, **kwargs)

        except FloodWaitError as e:
            # BUG FIX: Telegram иногда шлёт seconds=0 — защищаемся от зацикливания
            wait_seconds = max(1, e.seconds) + 5  # +5 для надёжности
            flood_attempts += 1
            if flood_attempts > MAX_FLOOD_RETRIES:
                logger.error(
                    f"[AntiBan] FloodWaitError после {MAX_FLOOD_RETRIES} попыток. Отдаём None."
                )
                return None
            logger.warning(
                f"[AntiBan] FloodWaitError ({flood_attempts}/{MAX_FLOOD_RETRIES}): "
                f"жду {wait_seconds}s (Telegram требует {e.seconds}s)"
            )
            await asyncio.sleep(wait_seconds)
            # Не увеличиваем attempt — FloodWait не считается сетевой ошибкой
            continue

        except SlowModeWaitError as e:
            wait_seconds = max(1, e.seconds) + 2
            logger.warning(f"[AntiBan] SlowModeWaitError: жду {wait_seconds}s")
            await asyncio.sleep(wait_seconds)
            continue

        except PeerFloodError:
            # Telegram считает нас спамером — длинная пауза
            flood_attempts += 1
            if flood_attempts > MAX_FLOOD_RETRIES:
                logger.error("[AntiBan] PeerFloodError: лимит попыток достигнут. Отдаём None.")
                return None
            logger.error(f"[AntiBan] PeerFloodError ({flood_attempts}/{MAX_FLOOD_RETRIES})! Жду 10 минут...")
            await asyncio.sleep(600)
            continue

        except (UserBannedInChannelError, ChatWriteForbiddenError) as e:
            # Нас забанили в чате — не ретраим
            logger.error(f"[AntiBan] Нет доступа к чату: {e}")
            return None

        except (ConnectionError, asyncio.TimeoutError) as e:
            # Сетевые ошибки — exponential backoff
            backoff = BASE_BACKOFF ** (attempt + 1)
            logger.warning(
                f"[AntiBan] Сетевая ошибка (попытка {attempt + 1}): {e}. "
                f"Жду {backoff:.1f}s..."
            )
            if attempt < MAX_NETWORK_RETRIES - 1:
                await asyncio.sleep(backoff)
            else:
                raise

    return None


def with_anti_ban(func: Callable) -> Callable:
    """
    Декоратор: оборачивает async-метод в safe_call.
    
    Использование:
        @with_anti_ban
        async def send_reply(client, chat_id, text):
            return await client.send_message(chat_id, text)
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await safe_call(func, *args, **kwargs)
    return wrapper
