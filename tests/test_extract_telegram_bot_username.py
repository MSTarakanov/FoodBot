from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "extract_telegram_bot_username.py"


def test_extract_telegram_bot_username_from_valid_get_me_response() -> None:
    result = run_script('{"ok": true, "result": {"username": "foodbot_prod"}}')

    assert result.returncode == 0
    assert result.stdout == "foodbot_prod\n"
    assert result.stderr == ""


def test_extract_telegram_bot_username_rejects_invalid_json() -> None:
    result = run_script("{")

    assert result.returncode == 1
    assert result.stdout == ""
    assert "not valid JSON" in result.stderr


def test_extract_telegram_bot_username_rejects_not_ok_response() -> None:
    result = run_script('{"ok": false, "description": "Unauthorized"}')

    assert result.returncode == 1
    assert result.stdout == ""
    assert "is not ok" in result.stderr


def test_extract_telegram_bot_username_rejects_missing_username() -> None:
    result = run_script('{"ok": true, "result": {"id": 123}}')

    assert result.returncode == 1
    assert result.stdout == ""
    assert "did not include bot username" in result.stderr


def run_script(payload: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        input=payload,
        text=True,
        capture_output=True,
        check=False,
    )
