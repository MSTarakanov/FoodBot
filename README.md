# Office Food Bot

Pre-alpha Telegram bot for office food coordination.

## Commands

- `/start` - introduces the bot.
- `/hi` - replies with a short greeting.

## Local Run

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
office-food-bot
```

Put the real bot token into `.env`. This file is local-only and is ignored by git.

For this pre-alpha the bot runs with long polling. Webhook deployment can be added when the
Render service exists.

## Runtime

The bot targets Python 3.14 in local development, CI, and VPS deployment.

## Checks

```bash
ruff check .
mypy src
pytest
```

## Testing Approach

Tests feed synthetic Telegram updates into the aiogram dispatcher. This keeps tests offline while
checking command routing and response text close to how a real user message is handled.
