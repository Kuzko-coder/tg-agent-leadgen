"""
packages/jobs/cleanup_job.py
──────────────────────────────
Фоновый job: удаление устаревших диалогов из SQLite.

Запускается каждые 24 часа.
Удаляет записи в таблице dialogs старше CLEANUP_OLDER_THAN_DAYS дней.

Использование:
    from packages.jobs.cleanup_job import start_cleanup_job

    asyncio.create_task(start_cleanup_job())
"""

import asyncio
import logging

from packages.config.settings import settings
from packages.database import repository

logger = logging.getLogger(__name__)


async def start_cleanup_job() -> None:
    """
    Бесконечный цикл очистки устаревших данных.
    Запускать как asyncio.Task при старте приложения.
    """
    interval_seconds = 24 * 3600  # 24 часа

    logger.info(
        f"[CleanupJob] Запущен. Интервал: 24ч. "
        f"Удаляем диалоги старше {settings.cleanup_older_than_days} дней"
    )

    while True:
        try:
            # Ждём до следующего запуска
            await asyncio.sleep(interval_seconds)

            deleted = await repository.prune_old_dialogs(
                days=settings.cleanup_older_than_days
            )
            logger.info(f"[CleanupJob] Удалено {deleted} устаревших записей из dialogs")

        except asyncio.CancelledError:
            logger.info("[CleanupJob] Остановлен")
            break
        except Exception as e:
            logger.error(f"[CleanupJob] Ошибка: {e}", exc_info=True)
            await asyncio.sleep(60)  # Пауза перед retry при ошибке
