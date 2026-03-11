"""
packages/agent/conversation_flow.py
─────────────────────────────────────
Трекер шагов OARS-диалога для каждого чата.

OARS шаги:
  1 = Открытый вопрос (Open question)
  2 = Отражение/Эмпатия (Affirm)
  3 = Рефлексия/Уточнение (Reflect)
  4 = Нативная рекомендация (Summary → Conversion)

Является тонкой обёрткой над LeadTracker с удобным API для агента.

Использование:
    from packages.agent.conversation_flow import conversation_flow

    step = await conversation_flow.get_step(chat_id)
    await conversation_flow.advance(chat_id)
    is_done = conversation_flow.is_completed(chat_id)
"""

import logging
from packages.memory.lead_tracker import lead_tracker

logger = logging.getLogger(__name__)

MAX_OARS_STEP = 4


class ConversationFlow:
    """
    Управляет последовательностью шагов OARS для каждого диалога.
    Делегирует персистентность в LeadTracker → Repository.
    """

    async def get_step(self, chat_id: int) -> int:
        """
        Возвращает текущий шаг OARS (1-4).
        """
        return await lead_tracker.get_step(chat_id)

    async def advance(self, chat_id: int) -> str:
        """
        Продвигает диалог на следующий шаг.
        :return: Новое состояние лида
        """
        new_state = await lead_tracker.advance(chat_id)
        step = await lead_tracker.get_step(chat_id)
        logger.info(
            f"[ConvFlow] chat_id={chat_id}: шаг {step}/{MAX_OARS_STEP}, "
            f"состояние={new_state}"
        )
        return new_state

    def is_completed(self, chat_id: int) -> bool:
        """
        Возвращает True если воронка завершена (шаг 4 достигнут).
        Используется для остановки дальнейших ответов агента.
        """
        return lead_tracker.is_converted(chat_id)

    async def get_step_description(self, chat_id: int) -> str:
        """Возвращает человекочитаемое описание текущего шага."""
        step = await self.get_step(chat_id)
        descriptions = {
            1: "открытый вопрос",
            2: "эмпатия и понимание",
            3: "уточнение деталей",
            4: "нативная рекомендация",
        }
        return descriptions.get(step, "неизвестный шаг")


# Синглтон
conversation_flow = ConversationFlow()
