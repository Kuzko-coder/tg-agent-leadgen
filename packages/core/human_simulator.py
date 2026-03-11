"""
packages/core/human_simulator.py
──────────────────────────────────
Имитация поведения живого человека в Telegram.

Функции:
  - read_acknowledge(client, chat_id) : отметить сообщение прочитанным
  - calculate_delay(text)             : вычислить Tsleep = len*0.1 + uniform(1,3)
  - simulate_typing(client, chat_id, duration) : показать статус "печатает"

Вся задержка и typing — ОБЯЗАТЕЛЬНЫ перед каждым ответом агента.

Использование:
    from packages.core.human_simulator import human_simulator

    await human_simulator.pre_response_sequence(client, chat_id, response_text)
"""

import asyncio
import random
import logging

from telethon import TelegramClient
from packages.core.anti_ban import safe_call

logger = logging.getLogger(__name__)


class HumanSimulator:
    """
    Симулирует поведение живого пользователя перед отправкой ответа.

    Последовательность:
    1. send_read_acknowledge — «прочитал сообщение»
    2. calculate_delay — считаем время «обдумывания»
    3. simulate_typing — показываем «печатает...»
    4. (агент отправляет сообщение)
    """

    def calculate_delay(self, response_text: str) -> float:
        """
        Динамическая задержка перед ответом.
        Формула: Tsleep = (длина_ответа × 0.1) + random(1.0, 3.0)

        Имитирует: чем длиннее ответ, тем дольше "пишет" человек.
        """
        base_delay = len(response_text) * 0.1
        random_delay = random.uniform(1.0, 3.0)
        total = base_delay + random_delay

        # Ограничиваем: минимум 2с, максимум 15с (реалистично)
        total = max(2.0, min(total, 15.0))
        logger.debug(f"[HumanSim] Задержка: {total:.1f}s (base={base_delay:.1f}, rnd={random_delay:.1f})")
        return total

    async def read_acknowledge(self, client: TelegramClient, chat_id: int) -> None:
        """
        Отмечает сообщения в чате как прочитанные.
        Человек сначала ЧИТАЕТ, потом пишет.
        """
        try:
            await safe_call(client.send_read_acknowledge, chat_id)
            logger.debug(f"[HumanSim] Read ack отправлен для chat_id={chat_id}")
        except Exception as e:
            # Не критично — продолжаем даже если не удалось
            logger.warning(f"[HumanSim] Read ack ошибка: {e}")

    async def simulate_typing(
        self,
        client: TelegramClient,
        chat_id: int,
        duration: float,
    ) -> None:
        """
        Показывает статус "печатает..." на протяжении `duration` секунд.
        Использует context manager Telethon: client.action(chat_id, 'typing').

        Telegram автоматически сбрасывает статус если не обновлять его.
        action() обновляет каждые ~5 секунд внутри контекста.
        """
        try:
            async with client.action(chat_id, "typing"):
                await asyncio.sleep(duration)
            logger.debug(f"[HumanSim] Typing симуляция: {duration:.1f}s в чате {chat_id}")
        except Exception as e:
            # Если typing не работает — просто ждём
            logger.warning(f"[HumanSim] Typing action ошибка: {e}")
            await asyncio.sleep(duration)

    async def pre_response_sequence(
        self,
        client: TelegramClient,
        chat_id: int,
        response_text: str,
    ) -> None:
        """
        Полная последовательность перед отправкой ответа:
        1. Read acknowledge (немедленно)
        2. Пауза 0.5–1.5с (читает сообщение)
        3. Typing на рассчитанное время

        :param client: Telethon клиент
        :param chat_id: ID чата
        :param response_text: Текст, который будет отправлен (для расчёта задержки)
        """
        # Шаг 1: Читаем сообщение
        await self.read_acknowledge(client, chat_id)

        # Шаг 2: Небольшая пауза как будто читаем
        read_pause = random.uniform(0.5, 1.5)
        await asyncio.sleep(read_pause)

        # Шаг 3: Показываем typing на вычисленное время
        delay = self.calculate_delay(response_text)
        await self.simulate_typing(client, chat_id, delay)


# Синглтон
human_simulator = HumanSimulator()
