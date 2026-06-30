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

## Contributor Flow

For everyday feature work, contributors do not need production tokens, VPS access, or deployment
secrets.

1. Create a branch named `feature/...`, `fix/...`, `docs/...`, or `chore/...`.
2. Run the bot locally with a personal development Telegram bot token.
3. Run local checks.
4. Push the branch.

GitHub creates a pull request and runs checks. A maintainer reviews and merges the pull request;
after `main` is updated, GitHub deploys the bot to the VPS.

## Testing Approach

Tests feed synthetic Telegram updates into the aiogram dispatcher. This keeps tests offline while
checking command routing and response text close to how a real user message is handled.

## GitHub Automation

Feature branches named `feature/**`, `fix/**`, `docs/**`, or `chore/**` can be turned into pull
requests automatically. Open pull requests are also updated from `main` when they are behind, so
strict branch protection can require fresh checks before merge.

`FOODBOT_AUTOMATION_TOKEN` is a repository secret used by GitHub Actions. It is a separate
fine-grained GitHub token for this repository with these permissions:

- Contents: read and write.
- Pull requests: read and write.

GitHub Actions also has a built-in `GITHUB_TOKEN`, but actions performed with it do not always
trigger the next workflow. This is intentional GitHub behavior that prevents accidental workflow
loops. The separate automation token makes the repository workflow explicit:

`push branch -> create PR -> run checks -> maintainer merge -> push main -> deploy`

Only maintainers need to manage this token. Contributors do not need it locally.

Auto-merge is currently disabled so maintainers can review pull requests before merge. The
mechanism is still kept for later: set the repository variable `FOODBOT_ENABLE_AUTO_MERGE` to
`true` and re-enable the `Enable Auto-Merge` workflow if automatic merging should come back.

## Deployment

Deployment runs on every push to `main` and can also be started manually from GitHub Actions.
The deploy workflow connects to the VPS over SSH and runs the fixed server-side deploy command.

Repository secrets:

- `FOODBOT_VPS_HOST` - VPS hostname or IP address.
- `FOODBOT_VPS_SSH_KEY` - private SSH key for deployment.
- `FOODBOT_VPS_PORT` - optional SSH port, defaults to `22`.
- `FOODBOT_VPS_USER` - optional SSH user, defaults to `root`.

Deployment secrets are maintainer-only. Contributors should only run the bot locally with their
own development Telegram bot token.

The matching public key on the server should be restricted with a forced command that runs
`/usr/local/sbin/deploy-foodbot`. The source version of that command is kept in
`deploy/deploy-foodbot.sh`.
