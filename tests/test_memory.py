"""
tests/test_memory.py
──────────────────────
Тесты для DialogMemory — менеджера памяти диалогов.

Проверяет:
  - Скользящее окно: 11 сообщений → хранится только 10
  - Добавление и получение сообщений
"""

import asyncio
import os
import tempfile
import pytest
import pytest_asyncio

# Используем временную БД для тестов
os.environ.setdefault("API_ID", "12345")
os.environ.setdefault("API_HASH", "test_hash")
os.environ.setdefault("GROK_API_KEY", "test_key")
os.environ.setdefault("PHONE_NUMBER", "+70000000000")

# Временный файл БД для изоляции тестов
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DB_PATH"] = _tmp_db.name
_tmp_db.close()


@pytest.fixture(autouse=True)
def setup_env(tmp_path):
    """Создаём свежую БД для каждого теста через временный путь."""
    import importlib
    # Переинициализируем dialog_memory для каждого теста
    pass


@pytest.mark.asyncio
async def test_rolling_window():
    """
    Если добавить 11 сообщений — в памяти должно остаться ровно 10.
    Это критично для передачи контекста в Grok (ограничение на 10 msg).
    """
    from packages.database.repository import init_db
    from packages.memory.dialog_memory import DialogMemory

    await init_db()
    memory = DialogMemory()  # Новый экземпляр (не синглтон) для теста

    chat_id = 999001

    # Добавляем 11 сообщений
    for i in range(11):
        await memory.add(chat_id, role="user", content=f"Сообщение {i}")

    history = await memory.get(chat_id)

    assert len(history) == 10, f"Ожидали 10 сообщений, получили {len(history)}"
    # Последнее сообщение должно быть 10-м (индексы 1-10)
    assert history[-1]["content"] == "Сообщение 10"
    # Первое сообщение (0) должно быть вытолкнуто
    assert all(m["content"] != "Сообщение 0" for m in history)


@pytest.mark.asyncio
async def test_add_and_get():
    """Базовый тест: добавить сообщения, получить их обратно."""
    from packages.database.repository import init_db
    from packages.memory.dialog_memory import DialogMemory

    await init_db()
    memory = DialogMemory()

    chat_id = 999002

    await memory.add(chat_id, role="user", content="Привет!")
    await memory.add(chat_id, role="assistant", content="Привет, как дела?")

    history = await memory.get(chat_id)

    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Привет!"}
    assert history[1] == {"role": "assistant", "content": "Привет, как дела?"}


@pytest.mark.asyncio
async def test_roles():
    """Проверяем что роли user/assistant сохраняются корректно."""
    from packages.database.repository import init_db
    from packages.memory.dialog_memory import DialogMemory

    await init_db()
    memory = DialogMemory()
    chat_id = 999003

    await memory.add(chat_id, role="user", content="test")
    history = await memory.get(chat_id)

    assert history[0]["role"] == "user"
