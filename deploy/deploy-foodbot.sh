#!/usr/bin/env bash
set -euo pipefail

exec 9>/var/lock/foodbot-deploy.lock
flock -n 9

repo=/opt/foodbot/repo
export GIT_TERMINAL_PROMPT=0

sudo -u foodbot -H git -C "$repo" fetch origin main
sudo -u foodbot -H git -C "$repo" reset --hard origin/main
sudo -u foodbot -H "$repo/.venv/bin/python" -m pip install -e "$repo"

systemctl restart foodbot.service
systemctl is-active foodbot.service
