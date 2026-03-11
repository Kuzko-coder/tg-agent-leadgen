"""
tests/test_trigger_filter.py
──────────────────────────────
Тесты для TriggerFilter — фильтра триггер-слов.

Проверяет:
  - First-shot rule: второй триггер в том же чате игнорируется
                     НО агент продолжает отвечать на ЛЮБЫЕ сообщения
  - Регистронезависимость поиска
  - Новый chat_id без триггера — пропускается
"""

import os
import pytest

os.environ.setdefault("API_ID", "12345")
os.environ.setdefault("API_HASH", "test_hash")
os.environ.setdefault("GROK_API_KEY", "test_key")
os.environ.setdefault("PHONE_NUMBER", "+70000000000")
os.environ.setdefault("TRIGGER_WORDS", "дизайн,интерьер,ремонт")


def get_fresh_filter():
    """Создаёт новый TriggerFilter для изоляции тестов."""
    from packages.agent.trigger_filter import TriggerFilter
    return TriggerFilter()


def test_trigger_activates_new_chat():
    """Триггер-слово в новом чате → should_process вернёт True."""
    tf = get_fresh_filter()
    assert tf.should_process(chat_id=1001, text="Хочу сделать дизайн квартиры") is True


def test_non_trigger_message_ignored():
    """Сообщение без триггера в новом чате → False."""
    tf = get_fresh_filter()
    assert tf.should_process(chat_id=1002, text="Привет, как дела?") is False


def test_case_insensitive_trigger():
    """Триггер в верхнем регистре тоже должен срабатывать."""
    tf = get_fresh_filter()
    assert tf.should_process(chat_id=1003, text="ДИЗАЙН кухни") is True
    assert tf.should_process(chat_id=1004, text="Интерьер") is True


def test_active_chat_responds_to_all_messages():
    """
    После первого триггера — агент должен отвечать на ВСЕ сообщения в чате,
    в том числе без триггер-слов.
    Это основная логика ведения диалога.
    """
    tf = get_fresh_filter()
    chat_id = 1005

    # Первое сообщение с триггером — активирует чат
    assert tf.should_process(chat_id, "хочу ремонт") is True

    # Следующие сообщения БЕЗ триггера — тоже обрабатываются (диалог идёт)
    assert tf.should_process(chat_id, "расскажи подробнее") is True
    assert tf.should_process(chat_id, "а сколько стоит?") is True
    assert tf.should_process(chat_id, "окей, интересно") is True


def test_different_chats_independent():
    """Разные chat_id не влияют друг на друга."""
    tf = get_fresh_filter()

    # Чат 1 активирован
    tf.should_process(1006, "дизайн")

    # Чат 2 без триггера — не активируется
    assert tf.should_process(1007, "просто привет") is False

    # Чат 1 продолжает работать
    assert tf.should_process(1006, "что-то ещё") is True


def test_release_deactivates_chat():
    """После release() чат перестаёт быть активным."""
    tf = get_fresh_filter()
    chat_id = 1008

    tf.should_process(chat_id, "интерьер")
    assert tf.is_active(chat_id) is True

    tf.release(chat_id)
    assert tf.is_active(chat_id) is False

    # Теперь снова нужен триггер
    assert tf.should_process(chat_id, "просто привет") is False


def test_get_active_count():
    """Счётчик активных чатов работает корректно."""
    tf = get_fresh_filter()

    tf.should_process(2001, "дизайн")
    tf.should_process(2002, "ремонт")
    tf.should_process(2003, "привет")  # не активируется

    assert tf.get_active_count() == 2
