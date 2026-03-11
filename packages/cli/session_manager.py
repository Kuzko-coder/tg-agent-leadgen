"""
packages/cli/session_manager.py
─────────────────────────────────
Менеджер сессий Telethon: сохранение и загрузка StringSession
с шифрованием через Fernet (cryptography library).

Файл сессии хранится в data/sessions/session.enc
Ключ шифрования хранится в .env (SESSION_FERNET_KEY)

При первом запуске:
  - Генерирует новый Fernet ключ
  - Сохраняет его в .env автоматически

Использование:
    from packages.cli.session_manager import session_manager

    session_manager.save_session(string_session)
    string_session = session_manager.load_session()
"""

import logging
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

SESSION_FILE = Path("data/sessions/session.enc")
ENV_FILE = Path(".env")


class SessionManager:
    """
    Шифрует StringSession через Fernet и хранит в файле.
    Ключ сохраняется в .env.
    """

    def _get_or_create_key(self) -> bytes:
        """
        Получает Fernet ключ из .env или генерирует новый.
        При генерации — записывает в .env автоматически.
        """
        # Пробуем из окружения (уже загружено через python-dotenv)
        key_str = os.environ.get("SESSION_FERNET_KEY", "").strip()

        if key_str:
            return key_str.encode()

        # Генерируем новый ключ
        new_key = Fernet.generate_key()
        logger.info("[SessionManager] Сгенерирован новый Fernet ключ")

        # Записываем в .env
        self._write_key_to_env(new_key.decode())
        os.environ["SESSION_FERNET_KEY"] = new_key.decode()

        return new_key

    def _write_key_to_env(self, key: str) -> None:
        """Обновляет или добавляет SESSION_FERNET_KEY в .env файл."""
        env_path = ENV_FILE

        if env_path.exists():
            content = env_path.read_text(encoding="utf-8")
            if "SESSION_FERNET_KEY=" in content:
                # Обновляем существующую строку
                lines = content.splitlines()
                new_lines = []
                for line in lines:
                    if line.startswith("SESSION_FERNET_KEY="):
                        new_lines.append(f"SESSION_FERNET_KEY={key}")
                    else:
                        new_lines.append(line)
                env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            else:
                # Добавляем новую строку
                with env_path.open("a", encoding="utf-8") as f:
                    f.write(f"\nSESSION_FERNET_KEY={key}\n")
        else:
            # Создаём .env если нет
            env_path.write_text(f"SESSION_FERNET_KEY={key}\n", encoding="utf-8")

        logger.info("[SessionManager] Fernet ключ сохранён в .env")

    def save_session(self, string_session: str) -> None:
        """
        Шифрует и сохраняет StringSession в файл.

        :param string_session: Строка сессии Telethon (StringSession.save())
        """
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)

        key = self._get_or_create_key()
        fernet = Fernet(key)

        encrypted = fernet.encrypt(string_session.encode())
        SESSION_FILE.write_bytes(encrypted)

        logger.info(f"[SessionManager] Сессия сохранена: {SESSION_FILE}")

    def load_session(self) -> Optional[str]:
        """
        Загружает и расшифровывает StringSession из файла.

        :return: Строка сессии или None если файл не найден
        """
        if not SESSION_FILE.exists():
            logger.info("[SessionManager] Файл сессии не найден")
            return None

        try:
            key = self._get_or_create_key()
            fernet = Fernet(key)

            encrypted = SESSION_FILE.read_bytes()
            decrypted = fernet.decrypt(encrypted).decode()

            logger.info("[SessionManager] Сессия успешно расшифрована")
            return decrypted

        except Exception as e:
            logger.error(f"[SessionManager] Ошибка расшифровки: {e}")
            return None

    def delete_session(self) -> None:
        """Удаляет файл сессии (logout)."""
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
            logger.info("[SessionManager] Файл сессии удалён")


# Синглтон
session_manager = SessionManager()
