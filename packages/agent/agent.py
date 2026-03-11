"""
packages/agent/agent.py
─────────────────────────
Главный оркестратор агента.

Связывает все слои системы в единый pipeline:
  Событие → Триггер-фильтр → БД (upsert лид) → Память → Промпт →
  Grok LLM → Reflection → HumanSim (read+typing) → Отправка → Память

Использование:
    from packages.agent.agent import AgentOrchestrator

    agent = AgentOrchestrator()
    await agent.process(event, client)
"""

import logging
from typing import Optional

from telethon import TelegramClient, events

from packages.memory.dialog_memory import dialog_memory
from packages.memory.lead_tracker import lead_tracker
from packages.llms.grok_client import grok_client
from packages.llms.prompt_builder import prompt_builder
from packages.llms.reflection import reflection_gate
from packages.core.human_simulator import human_simulator
from packages.core.anti_ban import safe_call
from packages.agent.conversation_flow import conversation_flow
from packages.agent.trigger_filter import trigger_filter
from packages.database import repository

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Основной оркестратор: получает событие NewMessage и выполняет
    полный цикл: анализ → генерация ответа → отправка.

    Архитектурный принцип: не хранит состояний сам.
    Всё состояние — в singleton-менеджерах (memory, lead_tracker, etc.)
    """

    async def process(
        self,
        event: events.NewMessage.Event,
        client: TelegramClient,
    ) -> None:
        """
        Полный pipeline обработки одного входящего сообщения.

        :param event: Telethon NewMessage event
        :param client: Активный TelegramClient для отправки ответа
        """
        chat_id = event.chat_id
        user_text = event.message.text
        sender = await event.get_sender()
        username = getattr(sender, "username", None)
        first_name = getattr(sender, "first_name", None)

        logger.info(
            f"[Agent] Обрабатываю сообщение от chat_id={chat_id} "
            f"(@{username}): {user_text[:50]}..."
        )

        try:
            # ── Шаг 1: Убедиться что лид есть в БД ───────────────────────
            await repository.upsert_lead(
                chat_id=chat_id,
                username=username,
                first_name=first_name,
            )

            # ── Шаг 2: Получить текущий шаг OARS ─────────────────────────
            oars_step = await conversation_flow.get_step(chat_id)

            # Если конверсия уже была — тихо выходим (не отвечаем)
            if conversation_flow.is_completed(chat_id):
                logger.info(
                    f"[Agent] chat_id={chat_id} уже конвертирован. Молчу."
                )
                return

            # ── Шаг 3: Добавить сообщение пользователя в память ──────────
            await dialog_memory.add(
                chat_id=chat_id,
                role="user",
                content=user_text,
            )

            # ── Шаг 4: Получить историю диалога ──────────────────────────
            history = await dialog_memory.get(chat_id)

            # ── Шаг 5: Построить системный промпт ────────────────────────
            system_prompt = prompt_builder.build(oars_step=oars_step)

            # ── Шаг 6: Генерация ответа через Grok ───────────────────────
            raw_reply = await grok_client.complete(
                messages=history,
                system_prompt=system_prompt,
            )

            # ── Шаг 7: Reflection gate — проверка и очистка ───────────────
            clean_reply = await reflection_gate.check(
                raw_reply=raw_reply,
                oars_step=oars_step,
                messages=history,
                system_prompt=system_prompt,
            )

            # ── Шаг 8: Имитация живого человека (read + typing) ───────────
            await human_simulator.pre_response_sequence(
                client=client,
                chat_id=chat_id,
                response_text=clean_reply,
            )

            # ── Шаг 9: Отправить ответ ────────────────────────────────────
            await safe_call(client.send_message, chat_id, clean_reply)
            logger.info(
                f"[Agent] Ответ отправлен в chat_id={chat_id}: "
                f"{clean_reply[:60]}..."
            )

            # ── Шаг 10: Сохранить ответ агента в память ───────────────────
            await dialog_memory.add(
                chat_id=chat_id,
                role="assistant",
                content=clean_reply,
            )

            # ── Шаг 11: Продвинуть шаг OARS воронки ──────────────────────
            new_state = await conversation_flow.advance(chat_id)
            logger.info(
                f"[Agent] chat_id={chat_id}: воронка → {new_state} "
                f"(шаг {oars_step} → {oars_step + 1})"
            )

            # ── Шаг 12: Если конвертировали — освобождаем триггер ─────────
            # (агент больше не будет инициировать новые диалоги в этом чате)
            # но продолжит отвечать если собеседник напишет ещё
            if new_state == "CONVERTED":
                logger.info(
                    f"[Agent] 🎉 Конверсия chat_id={chat_id}! "
                    f"(@{username})"
                )

        except Exception as e:
            logger.error(
                f"[Agent] Критическая ошибка при обработке chat_id={chat_id}: {e}",
                exc_info=True,
            )
            # При критической ошибке — не освобождаем чат, дадим retry
