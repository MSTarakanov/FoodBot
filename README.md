# Office Food Bot

Pre-alpha Telegram bot for office food coordination.

## Commands

The bot registers a Telegram slash menu on startup, so available commands are shown when a user
types `/` in Telegram. `/help` returns the same command set in chat.

Regular users see:

- `/start` - introduces the bot.
- `/help` - shows available commands.
- `/hi` - replies with a short greeting.
- `/register <name>` - asks an admin to approve a Telegram user with a display name.
- `/meta <minutes>` - says when a registered user will arrive.
- `/balance` - placeholder for the upcoming Splitwise balance view.

Admins also see:

- `/approve <telegram_user_id>` - approves a pending user.
- `/register_requests_list` - shows pending registration requests.

Admin command visibility is based on `TELEGRAM_ADMIN_IDS`. The `/approve` handler is protected too,
so non-admin users cannot approve registrations even if they type the command manually.

## Local Run

Prepare the project environment. If `uv` is not installed yet, setup will ask before installing it.

```bash
scripts/setup
uv run office-food-bot
```

Put the real bot token into `.env`. This file is local-only and is ignored by git.

## Configuration

Committed defaults live in `.env.defaults`. Use it for shared non-secret values such as
`DATABASE_PATH` and `FOODBOT_TIMEZONE`. It also keeps `TELEGRAM_ADMIN_IDS` as an empty required
key; real admin ids live in local `.env` files or GitHub Secrets.

The bot requires those keys to exist; keep shared defaults in `.env.defaults` instead of relying
on hidden Python fallback values.

Local overrides live in `.env`. `scripts/setup` creates it from `.env.example` if it does not
exist. Use `.env` for secrets such as `TELEGRAM_BOT_TOKEN`, and to override
`TELEGRAM_ADMIN_IDS` while debugging locally.

For this pre-alpha the bot runs with long polling.

## Runtime

The bot targets Python 3.14 in local development, CI, and VPS deployment.

## Checks

```bash
scripts/check
```

The script runs the same checks as CI:

```bash
uv run --extra dev ruff check .
uv run --extra dev mypy src
uv run --extra dev pytest
```

To run checks automatically before each commit in this clone:

```bash
scripts/setup
```

Git hook settings are local to each clone, so every contributor should run `scripts/setup` once
after cloning the repository.

## Local Telegram Testing

Use a separate development Telegram bot for local manual testing. Do not use the production
`TELEGRAM_BOT_TOKEN` while the production service is running, because Telegram long polling should
not be active from two places for the same bot token.

Recommended developer flow:

```bash
git clone git@github.com:MSTarakanov/FoodBot.git
cd FoodBot
scripts/setup
```

Create a personal development bot via `@BotFather`, then put its token into `.env`:

```env
TELEGRAM_BOT_TOKEN=your-development-bot-token
```

Run the bot locally:

```bash
uv run office-food-bot
```

Then open your development bot in Telegram and test commands such as `/start`, `/help`, `/hi`, and
any new command you are adding. If your local `.env` contains your Telegram user id in
`TELEGRAM_ADMIN_IDS`, the slash menu and `/help` should also include admin commands.

Before opening a pull request, also run:

```bash
scripts/check
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
- `FOODBOT_VPS_KNOWN_HOSTS` - pinned SSH host key for the VPS.
- `FOODBOT_VPS_PORT` - optional SSH port, defaults to `22`.
- `FOODBOT_VPS_USER` - optional SSH user, defaults to `root`.
- `TELEGRAM_BOT_TOKEN` - production Telegram bot token.
- `TELEGRAM_ADMIN_IDS` - comma-separated production Telegram admin user ids.

Deployment secrets are maintainer-only. Contributors should only run the bot locally with their
own development Telegram bot token.

The matching public key on the server should be restricted with a forced command that runs
`/usr/local/sbin/deploy-foodbot`. The source version of that command is kept in
`deploy/deploy-foodbot.sh`.

During deploy, GitHub Actions writes the production `/opt/foodbot/.env` on the VPS from secrets.
Local debugging still uses the uncommitted `.env` file in each developer clone.
