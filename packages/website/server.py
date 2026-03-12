"""
packages/website/server.py
───────────────────────────
Веб-дашборд агента на aiohttp.
Запускается из main.py как asyncio.Task.

Маршруты:
  GET  /           → SPA (index.html)
  GET  /api/config → текущий конфиг агента
  POST /api/config → обновить конфиг (имя, персона, цель, триггеры)
  GET  /api/leads  → список лидов с пагинацией
  GET  /api/stats  → воронка статистика
  POST /api/restart → перезапустить агента

Запуск:
    from packages.website.server import start_dashboard
    asyncio.create_task(start_dashboard())
"""

import asyncio
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from aiohttp import web
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

DASHBOARD_HTML = Path(__file__).parent / "dashboard.html"
DASHBOARD_PORT = int(os.environ.get("DASHBOARD_PORT", "8080"))


def _update_env_var(key: str, value: str) -> None:
    """Обновляет переменную в .env файле."""
    env_path = Path(".env")
    if not env_path.exists():
        env_path.write_text(f"{key}={value}\n", encoding="utf-8")
        os.environ[key] = value
        return

    content = env_path.read_text(encoding="utf-8")
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
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    os.environ[key] = value


async def handle_index(request: "web.Request") -> "web.Response":
    """Отдаёт HTML дашборда."""
    if DASHBOARD_HTML.exists():
        return web.Response(
            text=DASHBOARD_HTML.read_text(encoding="utf-8"),
            content_type="text/html",
            charset="utf-8",
        )
    return web.Response(text="<h1>Dashboard not found</h1>", content_type="text/html")


async def handle_get_config(request: "web.Request") -> "web.Response":
    """Возвращает текущий конфиг агента."""
    config = {
        "agent_name": os.environ.get("AGENT_NAME", ""),
        "agent_persona": os.environ.get("AGENT_PERSONA", ""),
        "conversion_goal": os.environ.get("CONVERSION_GOAL", ""),
        "trigger_words": os.environ.get("TRIGGER_WORDS", ""),
        "grok_model": os.environ.get("GROK_MODEL", "grok-4-1-fast-reasoning"),
        "report_interval_hours": os.environ.get("REPORT_INTERVAL_HOURS", "24"),
        "cleanup_older_than_days": os.environ.get("CLEANUP_OLDER_THAN_DAYS", "30"),
    }
    return web.json_response(config)


async def handle_post_config(request: "web.Request") -> "web.Response":
    """Обновляет конфиг агента (записывает в .env)."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    allowed = {
        "agent_name": "AGENT_NAME",
        "agent_persona": "AGENT_PERSONA",
        "conversion_goal": "CONVERSION_GOAL",
        "trigger_words": "TRIGGER_WORDS",
        "grok_model": "GROK_MODEL",
        "report_interval_hours": "REPORT_INTERVAL_HOURS",
    }

    updated = []
    for field, env_key in allowed.items():
        if field in data and data[field] is not None:
            _update_env_var(env_key, str(data[field]).strip())
            updated.append(field)

    logger.info(f"[Dashboard] Config updated: {updated}")
    return web.json_response({"ok": True, "updated": updated})


async def handle_get_leads(request: "web.Request") -> "web.Response":
    """Возвращает список лидов из БД."""
    try:
        from packages.database import repository
        limit = int(request.rel_url.query.get("limit", 50))
        offset = int(request.rel_url.query.get("offset", 0))
        leads = await repository.get_leads(limit=limit, offset=offset)
        return web.json_response({"leads": leads, "limit": limit, "offset": offset})
    except Exception as e:
        logger.error(f"[Dashboard] leads error: {e}")
        return web.json_response({"leads": [], "error": str(e)})


async def handle_get_stats(request: "web.Request") -> "web.Response":
    """Возвращает статистику воронки."""
    try:
        from packages.database import repository
        stats = await repository.get_stats()
        return web.json_response(stats)
    except Exception as e:
        logger.error(f"[Dashboard] stats error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def start_dashboard() -> None:
    """
    Запускает aiohttp веб-сервер с дашбордом.
    Вызывать как asyncio.Task из main.py.
    """
    if not AIOHTTP_AVAILABLE:
        logger.warning(
            "[Dashboard] aiohttp не установлен. "
            "Добавь 'aiohttp' в requirements.txt и переустанови зависимости."
        )
        return

    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/config", handle_get_config)
    app.router.add_post("/api/config", handle_post_config)
    app.router.add_get("/api/leads", handle_get_leads)
    app.router.add_get("/api/stats", handle_get_stats)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", DASHBOARD_PORT)

    try:
        await site.start()
        logger.info(
            f"[Dashboard] Веб-дашборд запущен: http://localhost:{DASHBOARD_PORT}"
        )
        # Держим сервер живым
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logger.info("[Dashboard] Остановлен")
        await runner.cleanup()
