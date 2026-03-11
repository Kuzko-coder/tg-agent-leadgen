"""
packages/database/models.py
────────────────────────────
Определение схемы SQLite базы данных через чистый aiosqlite (без ORM).

Таблицы:
  - dialogs  : история сообщений по chat_id (макс 10 на чат, чистится memory manager)
  - leads    : воронка лидов и их состояния
"""

# SQL-скрипты для создания таблиц

CREATE_DIALOGS_TABLE = """
CREATE TABLE IF NOT EXISTS dialogs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     INTEGER NOT NULL,
    role        TEXT    NOT NULL CHECK(role IN ('user', 'assistant')),
    content     TEXT    NOT NULL,
    created_at  REAL    NOT NULL DEFAULT (unixepoch('now'))
);
"""

# Индекс для быстрого поиска истории по chat_id
CREATE_DIALOGS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_dialogs_chat_id ON dialogs(chat_id, created_at);
"""

# Таблица лидов: одна запись на chat_id
CREATE_LEADS_TABLE = """
CREATE TABLE IF NOT EXISTS leads (
    chat_id          INTEGER PRIMARY KEY,
    username         TEXT,
    first_name       TEXT,
    oars_step        INTEGER NOT NULL DEFAULT 1,
    state            TEXT    NOT NULL DEFAULT 'NEW'
                             CHECK(state IN ('NEW', 'ENGAGED', 'WARM', 'CONVERTED')),
    triggered_at     REAL    NOT NULL DEFAULT (unixepoch('now')),
    converted_at     REAL,
    last_activity_at REAL    NOT NULL DEFAULT (unixepoch('now'))
);
"""

# Все SQL-скрипты для инициализации базы (порядок важен)
ALL_MIGRATIONS = [
    CREATE_DIALOGS_TABLE,
    CREATE_DIALOGS_INDEX,
    CREATE_LEADS_TABLE,
]
