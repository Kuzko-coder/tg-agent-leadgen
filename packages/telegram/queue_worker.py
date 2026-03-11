"""
packages/telegram/queue_worker.py
───────────────────────────────────
Асинхронный потребитель очереди сообщений.

Принимает события из asyncio.Queue (куда их кладёт handlers.py)
и передаёт их в агента для обработки.

Бесконечный цикл: queue.get() → agent.process(event) → queue.task_done()

Использование:
    from packages.telegram.queue_worker import run_queue_worker

    asyncio.create_task(run_queue_worker(queue, agent, client))
"""

import asyncio
import logging

from telethon import TelegramClient, events

logger = logging.getLogger(__name__)


async def run_queue_worker(
    queue: asyncio.Queue,
    agent,           # Type: AgentOrchestrator (избегаем circular import)
    client: TelegramClient,
) -> None:
    """
    Бесконечный цикл обработки очереди входящих событий.

    Обрабатывает события последовательно (по одному), чтобы:
    - Не отправлять параллельные ответы
    - Контролировать задержки между ответами

    :param queue: asyncio.Queue с событиями NewMessage
    :param agent: AgentOrchestrator с методом process(event, client)
    :param client: Telethon клиент для отправки ответов
    """
    logger.info("[QueueWorker] Запущен. Ожидаю события...")

    while True:
        try:
            # Ждём следующее событие из очереди (блокирующий вызов)
            event: events.NewMessage.Event = await queue.get()

            logger.debug(
                f"[QueueWorker] Получено событие из очереди. "
                f"В очереди ещё: {queue.qsize()}"
            )

            # Передаём в агента для обработки
            await agent.process(event, client)

            # Сигнализируем, что задача выполнена
            queue.task_done()

        except asyncio.CancelledError:
            # Graceful shutdown при отмене задачи
            logger.info("[QueueWorker] Остановлен (CancelledError)")
            break

        except Exception as e:
            # Не даём воркеру упасть из-за ошибки в одном сообщении
            logger.error(
                f"[QueueWorker] Ошибка при обработке события: {e}",
                exc_info=True,
            )
            # Осторожная пауза, чтобы не спамить логи при системных ошибках
            await asyncio.sleep(1.0)
            queue.task_done()
