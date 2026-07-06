#!/usr/bin/env python3
from __future__ import annotations

import json
import sys


def extract_telegram_bot_username(payload_text: str) -> str:
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as error:
        msg = "Telegram getMe response is not valid JSON"
        raise ValueError(msg) from error

    if not isinstance(payload, dict):
        msg = "Telegram getMe response must be an object"
        raise ValueError(msg)

    if payload.get("ok") is not True:
        msg = "Telegram getMe response is not ok"
        raise ValueError(msg)

    result = payload.get("result")
    if not isinstance(result, dict):
        msg = "Telegram getMe response result must be an object"
        raise ValueError(msg)

    username = result.get("username")
    if not isinstance(username, str) or not username.strip():
        msg = "Telegram getMe response did not include bot username"
        raise ValueError(msg)

    return username.strip()


def main() -> int:
    try:
        username = extract_telegram_bot_username(sys.stdin.read())
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(username)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
