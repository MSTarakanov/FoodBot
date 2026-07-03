# Contributing

## Fork-first setup

Contributors should work from a fork unless they own `MSTarakanov/FoodBot` or have collaborator
access.

```bash
git clone git@github.com:your-github-user/FoodBot.git
cd FoodBot
git remote add upstream git@github.com:MSTarakanov/FoodBot.git
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
itself. Without collaborator access, push to your fork and open a pull request.
Setup asks whether to re-check SSH, generate an ed25519 key and print its public
key for GitHub, continue without SSH, or stop setup.

## Local development

Use a personal Telegram development bot. `./setup-dev` asks for the bot token,
prints where to get it in `@BotFather`, rejects placeholder-looking values, and
can verify the token with Telegram before writing `.env`. If `.env` already has
a token, setup shows the bot username and `https://t.me/...` link before asking
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
2. Register the handler in `src/office_food_bot/commands/router.py`.
3. Add the slash-command metadata in `src/office_food_bot/commands/definitions.py`.
4. Add or update command tests in `tests/test_commands.py`.
5. Run `scripts/check`.
