# Contributing to TG Agent LeadGen

♥️ We welcome contributions from everyone.

## 🚀 Quick Start

### Development Setup

**Prerequisites:**
- macOS / Linux / WSL
- Python 3.10+
- An editor with Python/pytest support (VS Code recommended)

**Setup:**

```bash
git clone https://github.com/your-username/tg-agent-leadgen.git
cd tg-agent-leadgen
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Run tests:**

```bash
pytest tests/ -v
```

## 📁 Project Structure

This project follows a monorepo-style layout under `packages/`:

| Package | Description |
|---------|-------------|
| `config/` | Pydantic settings, .env loading |
| `database/` | SQLite models and async CRUD |
| `memory/` | Dialog memory (sliding window), lead state machine |
| `llms/` | Grok client, prompt builder, reflection gate |
| `core/` | Anti-ban protection, human behavior simulator |
| `telegram/` | Telethon client, event handlers, async queue |
| `agent/` | Main orchestrator, trigger filter, OARS flow tracker |
| `cli/` | Onboarding wizard, Fernet session manager |
| `jobs/` | Background jobs (queue worker, cleanup, daily report) |

## 🤝 How to Contribute

### Reporting Issues

- Use the [GitHub issue tracker](https://github.com/your-username/tg-agent-leadgen/issues)
- Search existing issues before creating new ones
- Provide clear reproduction steps for bugs
- Include Python version and OS details

### Code Contributions

**1. Fork and Clone:**

```bash
git clone https://github.com/your-username/tg-agent-leadgen.git
cd tg-agent-leadgen
```

**2. Create Feature Branch:**

```bash
git checkout -b feat/your-feature-name
```

**3. Make Changes:**
- Follow existing code style (async/await, type hints, docstrings)
- Add tests for new functionality in `tests/`
- Update documentation as needed

**4. Test Your Changes:**

```bash
pytest tests/ -v       # All tests must pass
```

**5. Commit and Push:**

```bash
git add .
git commit -m "feat: add awesome feature"
git push origin feat/your-feature-name
```

**6. Create Pull Request:**
- Provide clear description of changes
- Link related issues
- Include before/after screenshots for UI changes

## 🔧 Testing With Your Own Grok API

Create a `.env` file in the repo root:

```env
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash
PHONE_NUMBER=+7XXXXXXXXXX
GROK_API_KEY=xai-your-key-here
GROK_MODEL=grok-4-1-fast-reasoning
AGENT_NAME=YourAgent
AGENT_PERSONA=Your agent persona...
CONVERSION_GOAL=Your conversion goal
TRIGGER_WORDS=keyword1,keyword2
```

## 📝 Code Style

### General Guidelines

- Use Python type hints everywhere
- Follow async/await patterns (no blocking calls)
- Write docstrings for all public functions/classes
- Keep functions under 50 lines
- Singleton pattern for all service classes

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new feature
fix: fix a bug
docs: update documentation
test: add or update tests
refactor: refactor code without feature changes
chore: maintenance, dependency updates
```

### AI-Assisted Development

- AI assistance is **RECOMMENDED** for: documentation, tests, website
- AI assistance is **NOT allowed** for: core anti-ban logic, Telethon event handling
- **Always review** AI-generated code before committing
- You are the author of anything you commit — not the AI

## 🚫 What We Don't Accept

- Breaking changes without prior discussion in issues
- PRs without tests
- Code that doesn't follow async patterns
- Hardcoded credentials or API keys
- Contributions that encourage ToS violations
- Bot or AI-generated pull requests without meaningful human involvement

## 📄 Legal

By contributing to this project, you agree that your contributions will be licensed under the [MIT License](LICENSE).

## 💬 Questions?

- Open a [GitHub issue](https://github.com/your-username/tg-agent-leadgen/issues)
- Check existing documentation and issues first
- Be respectful and constructive in all discussions

Thank you for helping make TG Agent LeadGen better! 🎉
