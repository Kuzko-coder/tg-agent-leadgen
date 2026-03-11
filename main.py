"""
main.py
─────────
Точка входа приложения tg-agent-leadgen.

Порядок запуска:
  1. Настройка логирования
  2. Создание директорий (data/, data/sessions/)
  3. Проверка конфигурации → если нет .env → CLI Onboarding wizard
  4. Инициализация БД (CREATE TABLE IF NOT EXISTS)
  5. Получение Telethon клиента (StringSession)
  6. Создание asyncio.Queue
  7. Регистрация обработчиков событий
  8. Запуск всех задач через asyncio.gather:
      - Telethon run_until_disconnected
      - Queue worker
      - Cleanup job
      - Report job

Запуск: python main.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler

# ─── Загружаем .env до импорта settings ───────────────────────────────────
load_dotenv()

# ─── Настройка логирования ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(
            rich_tracebacks=True,
            show_path=True,
            markup=True,
        )
    ],
)
logger = logging.getLogger("tg-agent")

# Уменьшаем шум от Telethon
logging.getLogger("telethon").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

console = Console()


def ensure_directories() -> None:
    """Создаёт необходимые рабочие директории если их нет."""
    Path("data").mkdir(exist_ok=True)
    Path("data/sessions").mkdir(exist_ok=True)
    logger.info("Директории data/ и data/sessions/ готовы")


def check_configuration() -> bool:
    """
    Проверяет, заполнены ли минимальные переменные конфигурации.
    Возвращает False если нужен onboarding.
    """
    required = ["API_ID", "API_HASH", "GROK_API_KEY", "PHONE_NUMBER"]
    missing = [key for key in required if not os.environ.get(key, "").strip()]

    if missing:
        logger.warning(f"Не найдены обязательные переменные: {missing}")
        return False
    return True


async def main() -> None:
    """
    Главная async функция — точка входа.
    """
    console.print("[bold cyan]🤖 TG-Agent-Leadgen[/bold cyan] запускается...")

    # ── Шаг 1: Директории ─────────────────────────────────────────────────
    ensure_directories()

    # ── Шаг 2: Проверка конфигурации / Onboarding ─────────────────────────
    if not check_configuration():
        console.print("[yellow]Конфигурация не найдена. Запускаем wizard настройки...[/yellow]")
        console.print()

        from packages.cli.onboarding import run_onboarding
        await run_onboarding()

        # После onboarding перезагружаем .env
        load_dotenv(override=True)

        # Перезапускаем если нужно обновить settings
        console.print("[green]Настройка завершена! Перезапускаем агента...[/green]")
        os.execv(sys.executable, [sys.executable] + sys.argv)
        return

    # ── Шаг 3: Инициализация БД ───────────────────────────────────────────
    from packages.database.repository import init_db
    await init_db()
    logger.info("База данных инициализирована")

    # ── Шаг 4: Telethon клиент ────────────────────────────────────────────
    from packages.telegram.client import get_client
    client = await get_client()

    if not await client.is_user_authorized():
        console.print(
            "[red]Ошибка: пользователь не авторизован. "
            "Удали data/sessions/session.enc и запусти снова.[/red]"
        )
        sys.exit(1)

    me = await client.get_me()
    logger.info(f"Авторизован как: {me.first_name} (@{me.username})")

    # ── Шаг 5: Агент и очередь ────────────────────────────────────────────
    from packages.agent.agent import AgentOrchestrator
    agent = AgentOrchestrator()
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)

    # ── Шаг 6: Регистрируем обработчики событий ───────────────────────────
    from packages.telegram.handlers import register_handlers
    register_handlers(client, queue)

    # ── Шаг 7: Запускаем все фоновые задачи ──────────────────────────────
    from packages.jobs.message_queue_job import start_message_queue_job
    from packages.jobs.cleanup_job import start_cleanup_job
    from packages.jobs.report_job import start_report_job

    logger.info("Запускаем фоновые задачи...")

    queue_task = await start_message_queue_job(queue, agent, client)
    cleanup_task = asyncio.create_task(start_cleanup_job(), name="cleanup_job")
    report_task = asyncio.create_task(start_report_job(client), name="report_job")

    console.print(
        f"[bold green]✅ Агент запущен![/bold green] "
        f"Слушаю чаты по триггерам: [cyan]{os.environ.get('TRIGGER_WORDS', 'не настроено')}[/cyan]"
    )
    console.print("[dim]Нажми Ctrl+C для остановки[/dim]")

    try:
        # Основной цикл — работает пока Telethon подключён
        await client.run_until_disconnected()
    except KeyboardInterrupt:
        console.print("\n[yellow]Остановка по Ctrl+C...[/yellow]")
    finally:
        # Graceful shutdown
        queue_task.cancel()
        cleanup_task.cancel()
        report_task.cancel()

        await asyncio.gather(
            queue_task, cleanup_task, report_task,
            return_exceptions=True,
        )

        await client.disconnect()
        console.print("[bold cyan]Агент остановлен. До свидания![/bold cyan]")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
