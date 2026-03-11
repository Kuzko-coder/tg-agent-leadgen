"""
packages/config/settings.py
────────────────────────────
Централизованная конфигурация проекта через Pydantic BaseSettings.
Читает переменные из .env автоматически.

Использование:
    from packages.config.settings import settings
    print(settings.api_id)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """
    Все настройки агента.
    Переменные загружаются из .env файла или из переменных окружения.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Telegram ──────────────────────────────────────────────────────────
    api_id: int = Field(..., description="Telegram API ID с my.telegram.org")
    api_hash: str = Field(..., description="Telegram API Hash с my.telegram.org")
    phone_number: str = Field(..., description="Номер телефона в формате +7XXXXXXXXXX")

    # ── xAI Grok ─────────────────────────────────────────────────────────
    grok_api_key: str = Field(..., description="API ключ xAI Grok")
    grok_model: str = Field(
        default="grok-4-1-fast-reasoning",
        description="Идентификатор модели Grok",
    )
    grok_base_url: str = Field(
        default="https://api.x.ai/v1",
        description="Base URL для xAI API",
    )

    # ── Агент ─────────────────────────────────────────────────────────────
    agent_name: str = Field(default="Алина", description="Имя агента")
    agent_persona: str = Field(
        default="Обычный пользователь Telegram",
        description="Подробный портрет личности агента",
    )
    conversion_goal: str = Field(
        default="Познакомиться поближе",
        description="Цель конверсии (что агент должен сделать)",
    )

    # ── Триггеры ──────────────────────────────────────────────────────────
    # В .env хранится как строка: "дизайн,интерьер,ремонт"
    # Тут мы парсим в список
    trigger_words_raw: str = Field(
        default="",
        alias="trigger_words",
        description="Триггер-слова через запятую",
    )

    @property
    def trigger_words(self) -> List[str]:
        """Возвращает список триггер-слов в нижнем регистре."""
        return [w.strip().lower() for w in self.trigger_words_raw.split(",") if w.strip()]

    # ── Безопасность ──────────────────────────────────────────────────────
    session_fernet_key: str = Field(
        default="",
        description="Fernet ключ для шифрования StringSession (генерируется при onboarding)",
    )

    # ── База данных ───────────────────────────────────────────────────────
    db_path: str = Field(default="data/agent.db", description="Путь к SQLite базе")

    # ── Jobs ──────────────────────────────────────────────────────────────
    cleanup_older_than_days: int = Field(
        default=30,
        description="Удалять диалоги старше N дней",
    )
    report_interval_hours: int = Field(
        default=24,
        description="Интервал между отчётами (часы)",
    )
    report_recipient_id: int = Field(
        default=0,
        description="Telegram user_id для получения отчётов (0 = только консоль)",
    )

    def is_configured(self) -> bool:
        """
        Проверяет, прошёл ли пользователь onboarding.
        Минимальные условия: api_id, api_hash, grok_api_key заполнены.
        """
        try:
            return bool(self.api_id and self.api_hash and self.grok_api_key)
        except Exception:
            return False


# Синглтон — импортируем везде этот объект
settings = Settings()
