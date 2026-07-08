# Contributing

## Contributor setup

`./setup-dev` asks which Git contribution flow you want to use:

- `fork-first`: push feature branches to your fork, then open a pull request to
  `MSTarakanov/FoodBot`. This does not require write access to the main
  repository.
- `collaborator/direct`: push feature branches directly to
  `MSTarakanov/FoodBot`. This requires collaborator access.

External contributors can start fork-first:

```bash
git clone git@github.com:your-github-user/FoodBot.git
cd FoodBot
git remote add upstream git@github.com:MSTarakanov/FoodBot.git
./setup-dev
```

Owners and collaborators can work directly from `MSTarakanov/FoodBot`:

```bash
git clone git@github.com:MSTarakanov/FoodBot.git
cd FoodBot
./setup-dev
```

The setup command configures only this clone: local git identity, hooks, Python
environment, and `.env`. It does not write global git settings or install `uv`
globally. If `uv` is missing, setup installs it into `.tools/bin` and keeps uv
cache, managed Python, and `.venv` inside this repository. Use `./run ...` for
project commands or `scripts/uv ...` for lower-level uv commands, so the
repo-local paths are applied.

If GitHub SSH authentication is not ready, `./setup-dev` prints the steps for
creating an SSH key and adding the public key to GitHub. An SSH key authenticates
your GitHub account; it does not grant write access to the main repository by
itself.

In collaborator/direct mode, setup checks direct write access to
`MSTarakanov/FoodBot` with a dry-run push. If access is not confirmed, ask the
repository owner for collaborator access and re-run `./setup-dev` after accepting
the invite. Owner profile: <https://github.com/MSTarakanov>.

Create and push a feature branch:

```bash
git checkout -b feature/my-change
git push origin feature/my-change
```

Branches named `feature/**`, `fix/**`, `docs/**`, or `chore/**` in the main
repository open pull requests automatically.

The `main` branch is protected. Pull requests must pass CI and require review
from the code owner in `.github/CODEOWNERS`.

Maintainer note: to grant direct push access, open the repository settings and
use `MSTarakanov/FoodBot -> Settings -> Collaborators and teams -> Add people`.

## Local development

Use a personal Telegram development bot. `./setup-dev` asks for the bot token,
prints where to get it in `@BotFather`, rejects placeholder-looking values, and
verifies the token with Telegram before writing `.env`. If `.env` already has a
token, setup shows the bot username and `https://t.me/...` link before asking
whether to keep it.

To enable admin-only commands in your dev bot, let setup add your Telegram user
id to `TELEGRAM_ADMIN_IDS`. Setup prints how to get that id from `@userinfobot`
or `@RawDataBot`.

Re-run `./setup-dev` to update the current local setup. Use `./setup-dev
--reset-env` when you want to re-enter local git identity, ignore the existing
`.env` values, and answer the local Telegram configuration prompts from scratch.

## Agent-assisted setup

If an AI agent is helping with setup, keep secrets out of chat. The user should
type `TELEGRAM_BOT_TOKEN`, SSH key passphrases, and GitHub credentials directly
into a local terminal prompt.

Agents can run:

```bash
./setup-dev --agent-guide
```

Then the safe flow is:

1. The agent prepares the repository and explains the prompts.
2. The user runs `./setup-dev` in their own terminal, or the agent starts it only
   in a terminal where the user can type answers directly.
3. If SSH or the Telegram token is not ready, setup stops and prints the next
   concrete action.
4. After setup completes, the agent runs `scripts/check`.

Run the bot:

```bash
./run office-food-bot
```

Run checks:

```bash
scripts/check
```

## Adding a command

1. Add the handler in `src/office_food_bot/commands/`.
2. Send text, choice buttons, inline buttons, and polls through `BotMessenger`,
   not directly through `message.answer`, `bot.send_message`, or `bot.send_poll`.
3. Keep database access inside repositories and business rules inside services.
4. Register the handler in `src/office_food_bot/commands/router.py`.
5. Add the slash-command metadata in `src/office_food_bot/commands/definitions.py`.
6. For multi-step flows, add aiogram FSM states and keep validation in the active
   state handler until the answer is valid or the user runs another command.
7. For inline button callbacks, add `callback_query` handlers in the router.
8. Add or update command tests in `tests/test_commands.py`; add messenger tests
   in `tests/test_messaging.py` when introducing a new response primitive.
9. Run `scripts/check`.
