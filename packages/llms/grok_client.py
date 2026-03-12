"""
packages/llms/grok_client.py
───────────────────────────────
Асинхронный клиент для xAI Grok API через openai SDK.

xAI предоставляет OpenAI-совместимый API, поэтому используем
AsyncOpenAI с кастомным base_url.

Особенности:
  - Автоматический retry при RateLimitError (418/429)
  - Timeout 60 секунд на запрос
  - Логирование кол-ва токенов

Использование:
    from packages.llms.grok_client import grok_client

    reply = await grok_client.complete(messages=[...], system_prompt="...")
"""

import asyncio
import logging
from typing import List, Dict

from openai import AsyncOpenAI, RateLimitError, APITimeoutError, APIError

from packages.config.settings import settings

logger = logging.getLogger(__name__)


class GrokClient:
    """
    Синглтон-клиент для общения с xAI Grok API.
    Использует OpenAI SDK с кастомным base_url.
    """

    def __init__(self):
        self._client = AsyncOpenAI(
            api_key=settings.grok_api_key,
            base_url=settings.grok_base_url,
            timeout=60.0,
        )
        self._model = settings.grok_model

    async def complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        max_retries: int = 3,
        retry_delay: float = 5.0,
    ) -> str:
        """
        Отправляет запрос в Grok и возвращает текст ответа.

        :param messages: История диалога в формате OpenAI
                         [{"role": "user", "content": "..."}, ...]
        :param system_prompt: Системный промпт (персонаж + OARS + humanizer)
        :param max_retries: Максимальное количество повторных попыток
        :param retry_delay: Задержка между retry (секунды)
        :return: Текст ответа агента
        """
        # Формируем финальный массив: system + история диалога
        full_messages = [
            {"role": "system", "content": system_prompt},
            *messages,
        ]

        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"[Grok] Запрос #{attempt + 1}: модель={self._model}, "
                    f"сообщений={len(full_messages)}"
                )

                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=full_messages,
                    temperature=0.85,   # Небольшая вариативность для "живости"
                    max_tokens=512,     # Ответ не должен быть слишком длинным
                )

                # BUG FIX: choices может быть пустым при нестандартных ответах API
                if not response.choices:
                    logger.error("[Grok] Пустой список choices в ответе API")
                    continue

                reply = response.choices[0].message.content
                if not reply:
                    logger.warning("[Grok] Пустой content в ответе")
                    continue
                reply = reply.strip()

                # BUG FIX: usage может быть None если API не возвращает статистику
                usage = response.usage
                tokens_info = (
                    f"{usage.prompt_tokens}+{usage.completion_tokens}"
                    if usage else "N/A"
                )

                logger.info(
                    f"[Grok] Ответ получен: {len(reply)} символов | "
                    f"tokens: {tokens_info}"
                )
                return reply

            except RateLimitError as e:
                # Grok вернул 429 — ждём и повторяем
                wait_time = retry_delay * (attempt + 1)
                logger.warning(
                    f"[Grok] RateLimitError. Жду {wait_time}s перед retry..."
                )
                await asyncio.sleep(wait_time)

            except APITimeoutError:
                logger.warning(f"[Grok] Timeout на попытке {attempt + 1}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)

            except APIError as e:
                logger.error(f"[Grok] API ошибка: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    raise

        # Если все попытки исчерпаны — возвращаем заглушку
        logger.error("[Grok] Все попытки исчерпаны. Возвращаю fallback ответ.")
        return "Слушай, сейчас немного занята. Напишу чуть позже 🙂"


# Синглтон
grok_client = GrokClient()
