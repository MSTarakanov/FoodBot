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

## Local Telegram Testing

Use a separate development Telegram bot for local manual testing. Do not use the production
`TELEGRAM_BOT_TOKEN` while the production service is running, because Telegram long polling should
not be active from two places for the same bot token.

Recommended developer flow:

```bash
git clone git@github.com:MSTarakanov/FoodBot.git
cd FoodBot
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Create a personal development bot via `@BotFather`, then put its token into `.env`:

```env
TELEGRAM_BOT_TOKEN=your-development-bot-token
```

Run the bot locally:

```bash
office-food-bot
```

Then open your development bot in Telegram and test commands such as `/start`, `/hi`, and any new
command you are adding. Before opening a pull request, also run:

```bash
ruff check .
mypy src
pytest
```

## Testing Approach

Tests feed synthetic Telegram updates into the aiogram dispatcher. This keeps tests offline while
checking command routing and response text close to how a real user message is handled.

## GitHub Automation

Feature branches named `feature/**`, `fix/**`, `docs/**`, or `chore/**` can be turned into pull
requests automatically. Open pull requests are also updated from `main` when they are behind, so
strict branch protection can require fresh checks before merge.

For the full automation loop, add a repository secret named `FOODBOT_AUTOMATION_TOKEN`. Use a
fine-grained GitHub token for this repository with:

- Contents: read and write.
- Pull requests: read and write.
