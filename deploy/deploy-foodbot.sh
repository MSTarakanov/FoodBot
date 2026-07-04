#!/usr/bin/env bash
set -euo pipefail

exec 9>/var/lock/foodbot-deploy.lock
flock -n 9

repo=/opt/foodbot/repo
env_file=/opt/foodbot/.env
export GIT_TERMINAL_PROMPT=0

install_env_from_stdin() {
  if [ -t 0 ]; then
    return
  fi

  incoming_env="$(mktemp)"
  trap 'rm -f "$incoming_env"' RETURN
  cat > "$incoming_env"

  if [ ! -s "$incoming_env" ]; then
    return
  fi

  require_env_value "$incoming_env" FOODBOT_ENV
  require_env_value "$incoming_env" TELEGRAM_BOT_TOKEN
  require_env_value "$incoming_env" DATABASE_PATH
  require_env_value "$incoming_env" TELEGRAM_ADMIN_IDS
  require_env_value "$incoming_env" FOODBOT_TIMEZONE
  require_env_value "$incoming_env" SPLITWISE_API_KEY
  require_env_value "$incoming_env" SPLITWISE_GROUP_ID

  install -o foodbot -g foodbot -m 600 "$incoming_env" "$env_file"
}

require_env_value() {
  file="$1"
  key="$2"

  if ! grep -Eq "^${key}=.+" "$file"; then
    echo "Missing required $key in incoming environment file." >&2
    exit 1
  fi
}

install_env_from_stdin

sudo -u foodbot -H git -C "$repo" fetch origin main
sudo -u foodbot -H git -C "$repo" reset --hard origin/main
sudo -u foodbot -H "$repo/.venv/bin/python" -m pip install -e "$repo"

systemctl restart foodbot.service
systemctl is-active foodbot.service
