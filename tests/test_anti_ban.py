"""
tests/test_anti_ban.py
───────────────────────
Тесты для anti_ban.py — обработчика анти-бан защиты.

Проверяет:
  - При FloodWaitError(30) — ожидание ≥ 30 секунд (mocked)
  - При успешном вызове — результат возвращается
  - При UserBannedInChannelError — возвращается None без retry
"""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

os.environ.setdefault("API_ID", "12345")
os.environ.setdefault("API_HASH", "test_hash")
os.environ.setdefault("GROK_API_KEY", "test_key")
os.environ.setdefault("PHONE_NUMBER", "+70000000000")


@pytest.mark.asyncio
async def test_successful_call():
    """Успешный вызов возвращает результат напрямую."""
    from packages.core.anti_ban import safe_call

    async def mock_func():
        return "success"

    result = await safe_call(mock_func)
    assert result == "success"


@pytest.mark.asyncio
async def test_flood_wait_sleeps_correct_duration():
    """
    При FloodWaitError(seconds=30) — safe_call должен вызвать
    asyncio.sleep(35) (30 + 5 буфер), затем повторить вызов.
    """
    from telethon.errors import FloodWaitError
    from packages.core.anti_ban import safe_call

    sleep_calls = []
    call_count = 0

    async def mock_func():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # На первой попытке — FloodWaitError с 30 секундами
            error = FloodWaitError(request=None)
            error.seconds = 30
            raise error
        return "ok_after_flood"

    # Мокируем sleep чтобы не ждать реально (asyncio.coroutine удалён в Python 3.12)
    async def fake_sleep(secs):
        sleep_calls.append(secs)

    with patch("packages.core.anti_ban.asyncio.sleep", fake_sleep):
        result = await safe_call(mock_func)

    # Должен был поспать не менее 30+5=35 секунд
    assert len(sleep_calls) >= 1
    assert sleep_calls[0] >= 35, (
        f"Ожидали sleep(≥35), получили sleep({sleep_calls[0]})"
    )
    assert result == "ok_after_flood"


@pytest.mark.asyncio
async def test_banned_in_channel_returns_none():
    """
    При UserBannedInChannelError — немедленный возврат None без retry.
    """
    from telethon.errors import UserBannedInChannelError
    from packages.core.anti_ban import safe_call

    call_count = 0

    async def mock_func():
        nonlocal call_count
        call_count += 1
        raise UserBannedInChannelError(request=None)

    result = await safe_call(mock_func)

    assert result is None
    assert call_count == 1, f"Ожидали 1 попытку, было {call_count}"


@pytest.mark.asyncio
async def test_no_error_no_retry():
    """При отсутствии ошибок — функция вызывается ровно 1 раз."""
    from packages.core.anti_ban import safe_call

    call_count = 0

    async def mock_func():
        nonlocal call_count
        call_count += 1
        return 42

    result = await safe_call(mock_func)

    assert result == 42
    assert call_count == 1
