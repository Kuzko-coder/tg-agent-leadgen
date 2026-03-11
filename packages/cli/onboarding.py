"""
packages/cli/onboarding.py
────────────────────────────
Пошаговый CLI-wizard для первоначальной настройки агента.

Шаги:
  1. Запрос API_ID и API_HASH → сохранение в .env
  2. Авторизация по номеру телефона (Telethon)
  3. Имя агента и портрет личности
  4. Цель конверсии
  5. Триггер-слова
  6. GROK_API_KEY
  7. ID получателя отчётов (опционально)
  8. Сохранение StringSession (зашифрованное)

Использование:
    from packages.cli.onboarding import run_onboarding

    await run_onboarding()
"""

import asyncio
import os
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

from packages.cli.session_manager import session_manager

console = Console()
ENV_FILE = Path(".env")


def _write_env(key: str, value: str) -> None:
    """Записывает или обновляет переменную в .env файле."""
    if ENV_FILE.exists():
        content = ENV_FILE.read_text(encoding="utf-8")
        lines = content.splitlines()
        updated = False
        new_lines = []
        for line in lines:
            if line.startswith(f"{key}="):
                new_lines.append(f"{key}={value}")
                updated = True
            else:
                new_lines.append(line)
        if not updated:
            new_lines.append(f"{key}={value}")
        ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    else:
        with ENV_FILE.open("a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")
    # Также обновляем в os.environ для текущей сессии
    os.environ[key] = value


async def run_onboarding() -> None:
    """
    Запускает интерактивный wizard настройки агента.
    После завершения — все данные сохранены в .env и сессия зашифрована.
    """
    console.print(Panel(
        Text("🤖 TG-Agent-Leadgen — Настройка агента", justify="center", style="bold cyan"),
        subtitle="Первоначальная конфигурация",
    ))
    console.print()

    # ── Шаг 1: Telegram API ──────────────────────────────────────────────
    console.print("[bold yellow]Шаг 1/7[/] — Telegram API credentials")
    console.print(
        "Получи API_ID и API_HASH на [link=https://my.telegram.org]my.telegram.org[/link] "
        "→ API development tools"
    )
    console.print()

    api_id = Prompt.ask("  API_ID (число)")
    api_hash = Prompt.ask("  API_HASH")
    phone = Prompt.ask("  Номер телефона (формат: +79991234567)")

    _write_env("API_ID", api_id)
    _write_env("API_HASH", api_hash)
    _write_env("PHONE_NUMBER", phone)

    # ── Шаг 2: Авторизация Telegram ──────────────────────────────────────
    console.print()
    console.print("[bold yellow]Шаг 2/7[/] — Авторизация в Telegram")

    client = TelegramClient(
        session=StringSession(),
        api_id=int(api_id),
        api_hash=api_hash,
        device_model="iPhone 15 Pro",
        system_version="iOS 17.4.1",
        app_version="10.2.3",
        lang_code="ru",
        system_lang_code="ru-RU",
    )

    await client.connect()

    if not await client.is_user_authorized():
        await client.send_code_request(phone)
        console.print("  📱 Код отправлен на твой телефон")

        code = Prompt.ask("  Введи код из Telegram")

        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            # Двухфакторная аутентификация
            console.print("  🔐 У тебя включена двухфакторная аутентификация")
            password = Prompt.ask("  Введи пароль 2FA", password=True)
            await client.sign_in(password=password)

    me = await client.get_me()
    console.print(f"  ✅ Авторизован как: [green]{me.first_name}[/green] (@{me.username})")

    # Сохраняем зашифрованную StringSession
    string_session = client.session.save()
    session_manager.save_session(string_session)
    console.print("  🔐 Сессия зашифрована и сохранена")

    await client.disconnect()

    # ── Шаг 3: Личность агента ───────────────────────────────────────────
    console.print()
    console.print("[bold yellow]Шаг 3/7[/] — Личность агента")
    console.print("  Например: Алина, дизайнер интерьеров, 5 лет опыта, из Москвы")

    agent_name = Prompt.ask("  Имя агента")
    console.print("  Опиши persona агента (профессия, хобби, характер, откуда):")
    console.print("  [dim]Введи текст и нажми Enter дважды для завершения[/dim]")

    lines = []
    while True:
        line = input("  > ")
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)
    agent_persona = "\n".join(lines[:-1] if lines[-1] == "" else lines).strip()

    _write_env("AGENT_NAME", agent_name)
    _write_env("AGENT_PERSONA", agent_persona)

    # ── Шаг 4: Цель конверсии ────────────────────────────────────────────
    console.print()
    console.print("[bold yellow]Шаг 4/7[/] — Цель конверсии")
    console.print("  Например: «Порекомендовать курс по дизайну и дать ссылку xyz.ru»")

    conversion_goal = Prompt.ask("  Цель конверсии")
    _write_env("CONVERSION_GOAL", conversion_goal)

    # ── Шаг 5: Триггер-слова ─────────────────────────────────────────────
    console.print()
    console.print("[bold yellow]Шаг 5/7[/] — Триггер-слова")
    console.print("  Слова в чатах, которые запускают агента (через запятую)")
    console.print("  Например: дизайн,интерьер,ремонт,квартира")

    trigger_words = Prompt.ask("  Триггер-слова")
    _write_env("TRIGGER_WORDS", trigger_words)

    # ── Шаг 6: Grok API Key ──────────────────────────────────────────────
    console.print()
    console.print("[bold yellow]Шаг 6/7[/] — xAI Grok API Key")
    console.print("  Получи ключ на [link=https://x.ai]x.ai[/link] → API Keys")

    grok_key = Prompt.ask("  GROK_API_KEY", password=True)
    _write_env("GROK_API_KEY", grok_key)
    _write_env("GROK_MODEL", "grok-4-1-fast-reasoning")

    # ── Шаг 7: Получатель отчётов ────────────────────────────────────────
    console.print()
    console.print("[bold yellow]Шаг 7/7[/] — Получатель ежедневных отчётов")
    console.print("  Твой Telegram user_id (числовой ID, не username)")
    console.print("  Оставь пустым для отчётов только в консоль")

    recipient = Prompt.ask("  Telegram user_id для отчётов", default="0")
    _write_env("REPORT_RECIPIENT_ID", recipient)

    # ── Завершение ────────────────────────────────────────────────────────
    console.print()
    console.print(Panel(
        Text(
            f"✅ Настройка завершена!\n\n"
            f"Агент: {agent_name}\n"
            f"Цель: {conversion_goal}\n"
            f"Триггеры: {trigger_words}\n\n"
            f"Запусти снова: python main.py",
            justify="center",
        ),
        style="bold green",
    ))
