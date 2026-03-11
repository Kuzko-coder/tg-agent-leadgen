<div align="center">

<h1>🤖 TG Agent LeadGen</h1>

<p><strong>Автономный ИИ-агент для Telegram — лидогенерация на автопилоте</strong></p>

<p>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Telethon-MTProto-green" alt="Telethon">
  <img src="https://img.shields.io/badge/LLM-Grok%204.1-orange" alt="Grok 4.1">
  <img src="https://img.shields.io/badge/тестов-18%20прошли-brightgreen" alt="Tests">
</p>

<p>
  🌐 <a href="README.md">English</a> | <strong>Русский</strong>
</p>

</div>

---

## Что такое TG Agent LeadGen?

Автономный **Telegram userbot** (работает на вашем аккаунте), который:
- Слушает группы по триггер-словам
- Сам пишет людям — как живой человек
- Ведёт диалог по методу **OARS** (4 шага)
- Нативно закрывает на конверсию

Всё это на базе **Grok `grok-4-1-fast-reasoning`** (xAI) + **Telethon** (MTProto).

---

## ✨ Возможности

- 🧠 **Grok 4.1 Fast Reasoning** — самая быстрая рассуждающая модель от xAI
- 🗣️ **Метод OARS** — открытый вопрос → эмпатия → зондаж → нативная рекомендация
- 🕵️ **Имитация живого человека**:
  - `send_read_acknowledge` перед ответом (сначала читает)
  - `client.action('typing')` — показывает статус «печатает»
  - Динамическая задержка: `T = len(текст) × 0.1 + random(1, 3)` сек
- 🚫 **Анти-бан защита**:
  - `FloodWaitError` — засыпает ровно на столько, сколько требует Telegram + 5с
  - `PeerFloodError` — пауза 10 минут
  - Правило «Первого выстрела» — один триггер на чат, без спама
- 💾 **Локальная память** — скользящее окно 10 сообщений на `chat_id` (SQLite WAL)
- 🔐 **Шифрование сессии** — StringSession через Fernet encryption
- 📊 **Ежедневные отчёты** — статистика в консоль + Telegram ЛС
- 🧙 **CLI Wizard** — 7 шагов настройки при первом запуске (Rich UI)
- 🔍 **Reflection Gate** — фильтр перед отправкой: ИИ-штампы, давление продаж, самораскрытие → регенерация

---

## 💡 Примеры использования

| Кейс | Описание |
|------|----------|
| **Продажа курсов** | Мониторинг образовательных групп, вход при вопросах об обучении |
| **SaaS лидген** | Прослушка нишевых сообществ, предложение инструмента под боль |
| **Недвижимость/дизайн** | Таргетинг дискуссий про ремонт, ведение к консультации |
| **Community building** | Прогрев холодной аудитории через искренние диалоги |

---

## 🚀 Быстрый старт

### Требования

- Python 3.10+
- Аккаунт Telegram (не бот — userbot)
- API credentials с [my.telegram.org](https://my.telegram.org)
- xAI API key с [x.ai](https://x.ai)

### Установка

```bash
git clone https://github.com/your-username/tg-agent-leadgen.git
cd tg-agent-leadgen
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### Первый запуск (CLI Wizard)

```bash
python main.py
```

Wizard пошагово спросит:

1. `API_ID` и `API_HASH` (с my.telegram.org)
2. Авторизация по телефону (поддержка 2FA)
3. Имя агента и портрет личности
4. Цель конверсии
5. Триггер-слова
6. `GROK_API_KEY`
7. Telegram user ID для ежедневных отчётов

### Последующие запуски

```bash
python main.py
```

Агент стартует автоматически, используя сохранённую зашифрованную сессию.

---

## ⚙️ Конфигурация

Скопируй `.env.example` в `.env`:

```bash
cp .env.example .env
```

| Переменная | Описание |
|-----------|----------|
| `API_ID` | Telegram API ID |
| `API_HASH` | Telegram API Hash |
| `PHONE_NUMBER` | Номер телефона |
| `GROK_API_KEY` | xAI Grok API key |
| `GROK_MODEL` | `grok-4-1-fast-reasoning` |
| `AGENT_NAME` | Имя агента |
| `AGENT_PERSONA` | Подробное описание личности |
| `CONVERSION_GOAL` | Цель конверсии |
| `TRIGGER_WORDS` | Ключевые слова через запятую |
| `REPORT_RECIPIENT_ID` | Telegram ID для отчётов |

---

## 📁 Структура проекта

```
tg-agent-leadgen/
├── packages/
│   ├── config/        → Pydantic settings (.env)
│   ├── database/      → SQLite модели + async CRUD
│   ├── memory/        → Скользящее окно + машина состояний OARS
│   ├── llms/          → Grok client + prompt builder + reflection gate
│   ├── core/          → Анти-бан + имитация человека
│   ├── telegram/      → Telethon client + хэндлеры + очередь
│   ├── agent/         → Оркестратор + триггер-фильтр + OARS flow
│   ├── cli/           → Wizard + шифрование сессии
│   └── jobs/          → Очередь + очистка + отчёты
├── tests/             → 18 тестов (pytest + pytest-asyncio)
├── docs/              → GitHub Pages лендинг
├── main.py            → Точка входа
└── requirements.txt
```

---

## 🧠 Системный промпт (OARS + Humanizer)

Промпт — «секретный соус» человечности.

```
Шаг 1 → Открытый вопрос, искренний интерес. Никаких предложений.
Шаг 2 → Эмпатия к боли. «Я сама через это прошла». Решений нет.
Шаг 3 → Уточнение деталей. Намёк что решение существует.
Шаг 4 → Нативная рекомендация {цель_конверсии} как советский друг.
```

**Запрещённые слова** (humanizer-фильтры):
- «безусловно», «в современном мире», «давайте разберём», «идеальное решение»
- Никаких маркированных списков в сообщениях
- Не более 400 символов в одном ответе
- Никогда не признаваться что ты ИИ

---

## 🧪 Тесты

```bash
pytest tests/ -v
```

```
18 passed in 1.82s  ✅
```

---

## 🤝 Контрибьюция

См. [CONTRIBUTING.md](CONTRIBUTING.md) для настройки окружения.

Прочти [Code of Conduct](CODE_OF_CONDUCT.md) перед участием.

---

## ⚠️ Дисклеймер

Проект создан **в образовательных целях**. Использование userbot'ов может нарушать [Условия использования Telegram](https://telegram.org/tos). Используете на свой страх и риск.

---

## 📄 Лицензия

[MIT License](LICENSE) — Copyright (c) 2026
