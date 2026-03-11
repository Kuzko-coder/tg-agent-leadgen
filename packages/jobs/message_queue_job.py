"""
packages/jobs/message_queue_job.py
─────────────────────────────────────
Запускает очередь обработки сообщений как asyncio.Task.

Этот job — тонкая обёртка, которая создаёт и управляет
задачей run_queue_worker.

Использование:
    from packages.jobs.message_queue_job import start_message_queue_job

    task = await start_message_queue_job(queue, agent, client)
"""

import asyncio
import logging

from telethon import TelegramClient
from packages.telegram.queue_worker import run_queue_worker

logger = logging.getLogger(__name__)


async def start_message_queue_job(
    queue: asyncio.Queue,
    agent,
    client: TelegramClient,
) -> asyncio.Task:
    """
    Создаёт и возвращает asyncio.Task для обработки очереди сообщений.

    :param queue: asyncio.Queue с событиями от handlers.py
    :param agent: AgentOrchestrator
    :param client: Подключённый TelegramClient
    :return: Запущенная Task
    """
    task = asyncio.create_task(
        run_queue_worker(queue, agent, client),
        name="message_queue_worker",
    )
    logger.info("[MessageQueueJob] Воркер очереди запущен")
    return task
