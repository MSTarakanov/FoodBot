# Office Food Bot

Pre-alpha Telegram bot for office food coordination.

## Commands

The bot registers a Telegram slash menu on startup, so available commands are shown when a user
types `/` in Telegram. `/help` returns the same command set in chat.

Regular users see:

- `/start` - introduces the bot.
- `/help` - shows available commands.
- `/hi` - replies with a short greeting.
- `/register` - starts guided registration: the bot asks for a display name, then asks for a
  Splitwise email or lets the user skip Splitwise linking. A new registration overwrites an
  existing pending request for the same Telegram user.
  Already approved users see their current data and choose whether to send a
  re-registration request back to the pending approval list.
- `/meta <minutes>` - says when a registered user will arrive.
- `/balance` - placeholder for the upcoming Splitwise balance view.

Admins also see:

- `/approve <telegram_user_id>` - approves a pending user.
- `/register_requests_list` - shows pending registration requests.

Admin command visibility is based on `TELEGRAM_ADMIN_IDS`. The `/approve` handler is protected too,
so non-admin users cannot approve registrations even if they type the command manually.

## Local Run

Prepare the project environment. If `uv` is not installed yet, setup will ask before installing it
locally into `.tools/bin`. The setup command can be re-run at any time to update local git settings
or `.env`.

```bash
./setup-dev
./run office-food-bot
```

Use a personal development Telegram bot token in `.env`. This file is local-only and is ignored by
git. Setup prints where to get the token in `@BotFather`, rejects placeholder-looking values, and
verifies the token with Telegram before saving it. If `.env` already has a token, setup shows the
bot username and `https://t.me/...` link before asking whether to keep it.
Setup refuses to save the production Telegram bot token for local development.

## Configuration

Committed defaults live in `.env.defaults`. Use it for shared non-secret values such as
`FOODBOT_ENV`, `DATABASE_PATH`, `FOODBOT_TIMEZONE`, `SPLITWISE_GROUP_ID`, and
`PRODUCTION_TELEGRAM_BOT_ID`. It also keeps `TELEGRAM_ADMIN_IDS` as an empty required key; real
admin ids live in local `.env` files or GitHub Secrets.

The bot requires those keys to exist; keep shared defaults in `.env.defaults` instead of relying
on hidden Python fallback values.

Local overrides live in `.env`. `./setup-dev` creates or rewrites it interactively. Use `.env` for
secrets such as `TELEGRAM_BOT_TOKEN` and `SPLITWISE_API_KEY`, and to override
`TELEGRAM_ADMIN_IDS` or `SPLITWISE_GROUP_ID` while debugging locally.
Local `.env` uses `FOODBOT_ENV=development`; production deploy writes `FOODBOT_ENV=production`.
When running in development, the bot validates its token before polling and refuses to start if it
points at `PRODUCTION_TELEGRAM_BOT_ID`.
Re-run `./setup-dev` to update values while keeping existing answers by pressing Enter. Run
`./setup-dev --reset-env` to re-ask local git identity, ignore current `.env` values, and configure
them from scratch.
If an AI agent is helping with setup, run `./setup-dev --agent-guide` first and keep secrets out of
chat; enter tokens and credentials directly in a local terminal prompt.

For this pre-alpha the bot runs with long polling.

## Runtime

The bot targets Python 3.14 in local development, CI, and VPS deployment.
Local setup keeps downloaded tooling inside the clone: `uv` in `.tools/bin`, uv cache in
`.tools/uv-cache`, managed Python in `.tools/python`, and the project virtual environment in
`.venv`. Use `./run ...` for project commands or `scripts/uv ...` for lower-level uv commands, so
those local paths are used consistently.
For example, `./run office-food-bot` is the project-local equivalent of `uv run office-food-bot`.

## Checks

```bash
scripts/check
```

The script runs the same checks as CI:

```bash
scripts/uv run --extra dev ruff check .
scripts/uv run --extra dev mypy src
scripts/uv run --extra dev pytest
```

To run checks automatically before each commit in this clone:

```bash
./setup-dev
```

Git hook settings are local to each clone, so every contributor should run `./setup-dev` once after
cloning the repository. `scripts/setup` remains as a compatibility wrapper.

## Local Telegram Testing

Use a separate development Telegram bot for local manual testing. Do not use the production
`TELEGRAM_BOT_TOKEN` while the production service is running, because Telegram long polling should
not be active from two places for the same bot token.
The local runtime has a guard for this: if `.env` accidentally contains the production bot token,
`./run office-food-bot` exits before starting polling.

Recommended developer flow:

```bash
git clone git@github.com:your-github-user/FoodBot.git
cd FoodBot
git remote add upstream git@github.com:MSTarakanov/FoodBot.git
./setup-dev
```

Create a personal development bot via `@BotFather`; setup asks for its token and writes it to
`.env`. If you want admin commands in your dev bot, setup also prints how to get your Telegram user
id from `@userinfobot` or `@RawDataBot` and writes it to `TELEGRAM_ADMIN_IDS`.
`SPLITWISE_API_KEY` is required for local development. Each developer should create their own
Splitwise API key for their local clone. Do not share another developer's key: the key acts on
behalf of the Splitwise account that created it.

Run the bot locally:

```bash
./run office-food-bot
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

Repository owners and collaborators may keep `origin` on `MSTarakanov/FoodBot` and push branches
directly over SSH. External contributors should work fork-first: `origin` points to their fork and
`upstream` points to `MSTarakanov/FoodBot`.

1. Create a branch named `feature/...`, `fix/...`, `docs/...`, or `chore/...`.
2. Run the bot locally with a personal development Telegram bot token.
3. Run local checks.
4. Push the branch to your fork or to the main repository if you have collaborator access.

GitHub creates a pull request and runs checks. A maintainer reviews and merges the pull request;
after `main` is updated, GitHub deploys the bot to the VPS.

SSH authentication is required for SSH remotes. `./setup-dev` checks `git@github.com` and prints
instructions for creating an SSH key and adding the public key in GitHub Settings if authentication
is not ready. The SSH key authenticates your GitHub account; it does not grant write access to the
main repository by itself. If SSH is not ready, setup asks whether to re-check SSH, generate an
ed25519 key and print its public key for GitHub, continue without SSH, or stop setup.

## Adding a Command

1. Add the handler in `src/office_food_bot/commands/`.
2. Send text, choice buttons, inline buttons, and polls through `BotMessenger`,
   not directly through `message.answer`, `bot.send_message`, or `bot.send_poll`.
3. Keep database access inside repositories and business rules inside services.
4. Register the handler in `src/office_food_bot/commands/router.py`.
5. Add the slash-command metadata in `src/office_food_bot/commands/definitions.py`.
6. Use aiogram FSM states for multi-step flows. Ordinary text remains inside the
   active state until it validates; slash commands clear the active flow and run
   their own handler.
7. For inline button callbacks, add `callback_query` handlers in the router.
8. Add or update command tests in `tests/test_commands.py`; add messenger tests
   in `tests/test_messaging.py` when introducing a new response primitive.
9. Run `scripts/check`.

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
- `SPLITWISE_API_KEY` - production Splitwise API key.

Repository variables:

- `SPLITWISE_GROUP_ID` - optional override for the office Splitwise group id. If it is not set,
  deployment reads the value from `.env.defaults`.

Deployment secrets are maintainer-only. Contributors should only run the bot locally with their
own development Telegram bot token.

The matching public key on the server should be restricted with a forced command that runs
`/usr/local/sbin/deploy-foodbot`. The source version of that command is kept in
`deploy/deploy-foodbot.sh`.

During deploy, GitHub Actions writes the production `/opt/foodbot/.env` on the VPS from secrets.
Local debugging still uses the uncommitted `.env` file in each developer clone.
