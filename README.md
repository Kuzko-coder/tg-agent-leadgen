<div align="center">

<h1>🤖 TG Agent LeadGen</h1>

<p><strong>Autonomous Telegram AI Agent for Lead Generation</strong></p>

<p>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Telethon-MTProto-green" alt="Telethon">
  <img src="https://img.shields.io/badge/LLM-Grok%204.1-orange" alt="Grok 4.1">
  <img src="https://img.shields.io/badge/tests-18%20passed-brightgreen" alt="Tests">
</p>

<p>
  🌐 <strong><a href="README.md">English</a></strong> | <a href="README_RU.md">Русский</a>
</p>

<p>
  👉 <a href="https://Kuzko-coder.github.io/tg-agent-leadgen/"><strong>🚀 Live Demo</strong></a> |
  <a href="docs/"><strong>📖 Documentation</strong></a> |
  <a href="https://github.com/Kuzko-coder/tg-agent-leadgen/issues"><strong>🐛 Issues</strong></a>
</p>

</div>

---

## What is TG Agent LeadGen?

A **production-ready autonomous Telegram userbot** that listens to group chats for trigger keywords, engages prospects in natural human-like conversations, and guides them toward a conversion goal — all powered by **Grok `grok-4-1-fast-reasoning`** (xAI API).

The agent uses the **OARS method** (Open → Affirm → Reflect → Summary) to build rapport before pitching. It never says "click this link" in the first message. It listens first.

---

## ✨ Features

- 🧠 **Grok LLM Integration** (`grok-4-1-fast-reasoning`) — fastest reasoning model by xAI
- 🗣️ **OARS Conversation Method** — open question → empathy → soft recommendation
- 🕵️ **Human Behavior Simulation**:
  - `send_read_acknowledge` before replying (reads first)
  - `client.action('typing')` — shows typing indicator
  - Dynamic delay: `T = len(text) × 0.1 + random(1, 3)` seconds
- 🚫 **Anti-Ban Layer**:
  - `FloodWaitError` auto-sleep (exact seconds Telegram requires + 5s buffer)
  - `PeerFloodError` detection → 10-minute cooldown
  - First-shot rule: one trigger per chat, no spam
- 💾 **Local Memory** — 10-message sliding window per `chat_id` (SQLite WAL)
- 🔐 **Encrypted Sessions** — StringSession stored with Fernet encryption
- 📊 **Daily Reports** — stats to console **and** Telegram DM
- 🧙 **CLI Onboarding Wizard** — 7-step setup on first run (Rich terminal UI)
- 🔍 **Reflection Gate** — checks every reply for AI tells, sales pressure, banned phrases → regenerates automatically

---

## 💡 Use Cases

| Use Case | Description |
|----------|-------------|
| **Course Promotion** | Monitor educational groups, engage when someone asks about learning |
| **SaaS Lead Gen** | Listen for pain points in niche communities, offer your tool |
| **Real Estate** | Target renovation/design discussions, guide to consultations |
| **Community Building** | Warm up cold audiences with genuine conversations |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Telegram account (not a bot — a userbot)
- API credentials from [my.telegram.org](https://my.telegram.org)
- xAI API key from [x.ai](https://x.ai)

### Installation

```bash
git clone https://github.com/Kuzko-coder/tg-agent-leadgen.git
cd tg-agent-leadgen
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### First Run (CLI Wizard)

```bash
python main.py
```

The wizard will ask you step-by-step:

1. `API_ID` and `API_HASH` (from my.telegram.org)
2. Phone number authorization (with 2FA support)
3. Agent name and persona description
4. Conversion goal
5. Trigger keywords
6. `GROK_API_KEY`
7. Telegram user ID for daily reports

### Subsequent Runs

```bash
python main.py
```

Agent starts automatically using saved (encrypted) session.

---

## ⚙️ Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `API_ID` | Telegram API ID |
| `API_HASH` | Telegram API Hash |
| `PHONE_NUMBER` | Your phone number |
| `GROK_API_KEY` | xAI Grok API key |
| `GROK_MODEL` | `grok-4-1-fast-reasoning` |
| `AGENT_NAME` | Agent's display name |
| `AGENT_PERSONA` | Detailed personality description |
| `CONVERSION_GOAL` | What the agent should lead to |
| `TRIGGER_WORDS` | Comma-separated keywords |
| `REPORT_RECIPIENT_ID` | Telegram user ID for reports |

---

## 📁 Project Structure

```
tg-agent-leadgen/
├── packages/
│   ├── config/        → Pydantic settings (.env loader)
│   ├── database/      → SQLite models + async CRUD
│   ├── memory/        → 10-msg sliding window + OARS state machine
│   ├── llms/          → Grok client + prompt builder + reflection gate
│   ├── core/          → Anti-ban layer + human behavior simulator
│   ├── telegram/      → Telethon client + event handlers + queue
│   ├── agent/         → Main orchestrator + trigger filter + OARS flow
│   ├── cli/           → Onboarding wizard + Fernet session manager
│   └── jobs/          → Message queue job + cleanup job + report job
├── tests/             → 18 unit tests (pytest + pytest-asyncio)
├── docs/              → GitHub Pages landing page
├── main.py            → Entry point
└── requirements.txt
```

---

## 🧠 System Prompt Design (OARS + Humanizer)

The prompting strategy is the core "secret sauce":

```
Step 1 → Ask open question, show genuine interest
Step 2 → Acknowledge their pain/problem with empathy. NO solutions yet.
Step 3 → Gently probe details. Hint a solution exists, don't reveal it.
Step 4 → Natively recommend {conversion_goal} as a friendly next step.
```

**Humanizer Filters** (strictly banned):
- "absolutely", "in today's world", "let's explore", "optimal solution"
- No bullet points in messages
- No long monologues (max 400 chars per reply)
- Never admit to being an AI

**Writing Style:**
- Active voice, short sentences
- Burstiness: alternate very short (2–5 words) and medium sentences
- Conversational openers: "so", "look", "by the way", "listen"

---

## 🧪 Tests

```bash
pytest tests/ -v
```

```
18 passed in 1.82s  ✅
```

| Test File | Coverage |
|-----------|----------|
| `test_memory.py` | Rolling window, add/get, role preservation |
| `test_prompt_builder.py` | No banned words, OARS step diff, name injection, boundaries |
| `test_trigger_filter.py` | Case-insensitive, first-shot, active chat tracking |
| `test_anti_ban.py` | FloodWait exact sleep, ban error handling |

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and contribution guide.

Please read the [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

---

## ⚠️ Disclaimer

This project is for **educational purposes only**. Using userbots may violate [Telegram's Terms of Service](https://telegram.org/tos). Use at your own risk. The authors are not responsible for any account bans or misuse.

---

## 📄 License

[MIT License](LICENSE) — Copyright (c) 2026
