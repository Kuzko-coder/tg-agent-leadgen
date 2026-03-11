"""
packages/llms/reflection.py
──────────────────────────────
Reflection-before-action: фильтр качества ответа перед отправкой.

Проверяет сгенерированный ответ Grok на:
  1. Наличие запрещённых ИИ-штампов
  2. Слишком "продажный" тон (прямое предложение до шага 4)
  3. Слишком длинный ответ (> 400 символов)
  4. Упоминание о том, что агент является ИИ/ботом

Если проблема найдена — запрашивает регенерацию у Grok (до 2 попыток).

Использование:
    from packages.llms.reflection import reflection_gate

    clean_reply = await reflection_gate.check(
        raw_reply="...", oars_step=2, messages=[...])
"""

import logging
import re
from typing import List, Dict

from packages.llms.grok_client import grok_client
from packages.llms.prompt_builder import BANNED_PHRASES

logger = logging.getLogger(__name__)

# Паттерны, указывающие на "продажный" тон (для шагов 1-3)
SALES_PATTERNS = [
    r"предлаг\w+",          # "предлагаю", "предлагаем"
    r"рекоменд\w+ тебе",    # "рекомендую тебе"
    r"перейди по ссылке",
    r"https?://",           # Прямые ссылки — только на шаге 4
    r"акция",
    r"скидка",
    r"купи",
    r"приобрети",
]

# Паттерны, выдающие ИИ/бота
AI_REVEAL_PATTERNS = [
    r"\bя (языковая|языковая) модель\b",
    r"\bя (ии|ИИ|AI|искусственный интеллект)\b",
    r"\bя (бот|bot)\b",
    r"\bкак (ии|AI|ИИ)\b",
    r"\bкак (нейросеть|нейро)\b",
    r"в качестве (ии|AI|ИИ|бота)",
]

MAX_REPLY_LENGTH = 400  # Максимальная длина ответа в символах
MAX_REGENERATE_ATTEMPTS = 2


class ReflectionGate:
    """
    Пре-отправочный фильтр: проверяет ответ Grok и при необходимости
    запрашивает регенерацию с уточняющим промптом.
    """

    def _has_banned_phrases(self, text: str) -> bool:
        """Проверяет наличие запрещённых ИИ-штампов."""
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in BANNED_PHRASES)

    def _has_sales_patterns(self, text: str, oars_step: int) -> bool:
        """На шагах 1-3 прямые продажи запрещены."""
        if oars_step >= 4:
            return False
        text_lower = text.lower()
        return any(re.search(p, text_lower) for p in SALES_PATTERNS)

    def _reveals_ai(self, text: str) -> bool:
        """Проверяет, раскрывает ли ответ что агент — ИИ."""
        text_lower = text.lower()
        return any(re.search(p, text_lower) for p in AI_REVEAL_PATTERNS)

    def _is_too_long(self, text: str) -> bool:
        """Ответ не должен быть длинным монологом."""
        return len(text) > MAX_REPLY_LENGTH

    def _find_issues(self, text: str, oars_step: int) -> List[str]:
        """Собирает список найденных проблем."""
        issues = []
        if self._has_banned_phrases(text):
            issues.append("содержит запрещённые ИИ-штампы")
        if self._has_sales_patterns(text, oars_step):
            issues.append(f"содержит прямую продажу на шаге {oars_step} (нужен шаг 4)")
        if self._reveals_ai(text):
            issues.append("раскрывает, что агент является ИИ/ботом")
        if self._is_too_long(text):
            issues.append(f"слишком длинный ({len(text)} символов, макс {MAX_REPLY_LENGTH})")
        return issues

    def _build_correction_prompt(self, original: str, issues: List[str]) -> str:
        """Строит промпт для регенерации с указанием проблем."""
        issues_text = "\n".join(f"  - {issue}" for issue in issues)
        return (
            f"Предыдущий ответ содержал ошибки:\n{issues_text}\n\n"
            f"Предыдущий ответ: «{original}»\n\n"
            f"Перефразируй его, устранив все перечисленные проблемы. "
            f"Придерживайся того же смысла и тона, но без ошибок. "
            f"Ответ должен быть коротким (до 3 предложений)."
        )

    async def check(
        self,
        raw_reply: str,
        oars_step: int,
        messages: List[Dict[str, str]],
        system_prompt: str,
    ) -> str:
        """
        Проверяет ответ и при необходимости регенерирует его.

        :param raw_reply: Исходный ответ от Grok
        :param oars_step: Текущий шаг OARS
        :param messages: История диалога (для контекста регенерации)
        :param system_prompt: Системный промпт (для регенерации)
        :return: Очищенный ответ
        """
        current_reply = raw_reply

        for attempt in range(MAX_REGENERATE_ATTEMPTS):
            issues = self._find_issues(current_reply, oars_step)

            if not issues:
                # Ответ чистый — отправляем как есть
                if attempt > 0:
                    logger.info(f"[Reflection] Ответ принят на попытке {attempt + 1}")
                return current_reply

            logger.warning(
                f"[Reflection] Попытка {attempt + 1}: найдены проблемы: {issues}"
            )

            # Строим корректирующий запрос
            correction_messages = messages + [
                {"role": "assistant", "content": current_reply},
                {"role": "user", "content": self._build_correction_prompt(current_reply, issues)},
            ]

            current_reply = await grok_client.complete(
                messages=correction_messages,
                system_prompt=system_prompt,
            )

        # После всех попыток — используем последний вариант и логируем
        final_issues = self._find_issues(current_reply, oars_step)
        if final_issues:
            logger.error(
                f"[Reflection] После {MAX_REGENERATE_ATTEMPTS} попыток "
                f"проблемы не устранены: {final_issues}. Используем как есть."
            )

        return current_reply


# Синглтон
reflection_gate = ReflectionGate()
