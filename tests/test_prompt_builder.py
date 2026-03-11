"""
tests/test_prompt_builder.py
──────────────────────────────
Тесты для PromptBuilder — генератора системного промпта.

Проверяет:
  - Промпт не содержит запрещённых ИИ-штампов
  - Разные шаги OARS генерируют разный контент
  - Имя агента и цель подставляются корректно
"""

import os
import pytest

os.environ.setdefault("API_ID", "12345")
os.environ.setdefault("API_HASH", "test_hash")
os.environ.setdefault("GROK_API_KEY", "test_key")
os.environ.setdefault("PHONE_NUMBER", "+70000000000")
os.environ.setdefault("AGENT_NAME", "Тест")
os.environ.setdefault("AGENT_PERSONA", "Тестовый агент для тестирования")
os.environ.setdefault("CONVERSION_GOAL", "Тестовая цель конверсии")


def test_no_banned_words_in_prompt():
    """
    Системный промпт не должен сам содержать слова из списка BANNED_PHRASES.
    Если он их содержит — это баг (промпт учит то, что сам нарушает).
    """
    from packages.llms.prompt_builder import prompt_builder, BANNED_PHRASES

    for step in range(1, 5):
        prompt = prompt_builder.build(oars_step=step)
        prompt_lower = prompt.lower()

        # Исключение: в промпте эти слова могут стоять в СПИСКЕ ЗАПРЕТОВ
        # (в кавычках), но НЕ в инструкциях. Проверяем только вне кавычек.
        # Упрощённая проверка: просто считаем вхождения без контекста кавычек
        # — достаточно для основной валидации
        content_without_quotes = prompt.split("ЗАПРЕТЫ")[0] if "ЗАПРЕТЫ" in prompt else prompt
        content_lower = content_without_quotes.lower()

        forbidden_found = [p for p in BANNED_PHRASES if p in content_lower]
        assert not forbidden_found, (
            f"Шаг {step}: промпт содержит запрещённые паттерны "
            f"вне секции ЗАПРЕТЫ: {forbidden_found}"
        )


def test_different_steps_produce_different_instructions():
    """Каждый шаг OARS должен давать уникальную инструкцию."""
    from packages.llms.prompt_builder import prompt_builder

    prompts = [prompt_builder.build(oars_step=step) for step in range(1, 5)]

    # Все 4 промпта должны быть разными
    for i in range(len(prompts)):
        for j in range(i + 1, len(prompts)):
            assert prompts[i] != prompts[j], (
                f"Шаг {i+1} и шаг {j+1} дают одинаковый промпт!"
            )


def test_agent_name_in_prompt():
    """Имя агента из настроек должно быть в промпте."""
    from packages.llms.prompt_builder import prompt_builder

    prompt = prompt_builder.build(oars_step=1)
    assert "Тест" in prompt, "Имя агента не найдено в промпте"


def test_step_boundaries():
    """Шаги за пределами 1-4 должны корректно обрабатываться."""
    from packages.llms.prompt_builder import prompt_builder

    # Шаг 0 → должен работать как 1
    prompt_zero = prompt_builder.build(oars_step=0)
    prompt_one = prompt_builder.build(oars_step=1)
    assert prompt_zero == prompt_one

    # Шаг 5 → должен работать как 4
    prompt_five = prompt_builder.build(oars_step=5)
    prompt_four = prompt_builder.build(oars_step=4)
    assert prompt_five == prompt_four
