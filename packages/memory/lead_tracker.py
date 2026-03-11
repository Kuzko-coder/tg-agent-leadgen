"""
packages/memory/lead_tracker.py
────────────────────────────────
Трекер конверсионного состояния лида — обёртка над репозиторием.

Машина состояний:
  NEW → ENGAGED → WARM → CONVERTED

Связывает oars_step (1-4) с состоянием воронки.
Предоставляет быстрый доступ к текущему шагу без лишних запросов в БД.

Использование:
    from packages.memory.lead_tracker import lead_tracker

    step = await lead_tracker.get_step(chat_id)
    new_state = await lead_tracker.advance(chat_id)
"""

from typing import Dict
from packages.database import repository


class LeadTracker:
    """
    In-memory кэш шагов OARS для лидов.
    Синхронизируется с БД при каждом продвижении.
    """

    def __init__(self):
        # chat_id -> oars_step (1..4)
        self._steps: Dict[int, int] = {}

    async def get_step(self, chat_id: int) -> int:
        """
        Возвращает текущий шаг OARS (1-4).
        При первом вызове загружает из БД.
        """
        if chat_id not in self._steps:
            lead = await repository.get_lead(chat_id)
            self._steps[chat_id] = lead["oars_step"] if lead else 1
        return self._steps[chat_id]

    async def get_state(self, chat_id: int) -> str:
        """Возвращает строковое состояние лида (NEW/ENGAGED/WARM/CONVERTED)."""
        lead = await repository.get_lead(chat_id)
        return lead["state"] if lead else "NEW"

    async def advance(self, chat_id: int) -> str:
        """
        Продвигает лида на следующий шаг OARS.
        Обновляет кэш и персистирует в БД.

        :return: Новое строковое состояние
        """
        new_state = await repository.advance_lead_step(chat_id)
        # Обновляем локальный кэш
        lead = await repository.get_lead(chat_id)
        if lead:
            self._steps[chat_id] = lead["oars_step"]
        return new_state

    def is_converted(self, chat_id: int) -> bool:
        """Быстрая проверка: достиг ли лид шага 4 (CONVERTED)."""
        return self._steps.get(chat_id, 1) >= 4

    def reset(self, chat_id: int) -> None:
        """Сбрасывает кэшированный шаг (например, при реинициализации)."""
        self._steps.pop(chat_id, None)


# Синглтон
lead_tracker = LeadTracker()
