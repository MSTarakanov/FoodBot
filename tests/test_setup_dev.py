from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETUP_DEV = ROOT / "scripts" / "setup-dev"


def run_env_setup(
    tmp_path: Path,
    user_input: str,
    *extra_args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SETUP_DEV), "--env-only", "--skip-token-check", *extra_args],
        cwd=tmp_path,
        input=user_input,
        text=True,
        capture_output=True,
        check=True,
    )


def read_env(tmp_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (tmp_path / ".env").read_text(encoding="utf-8").splitlines():
        key, value = line.split("=", 1)
        values[key] = value
    return values


def test_setup_dev_creates_env_with_admin_id(tmp_path: Path) -> None:
    result = run_env_setup(tmp_path, "123456:test-token\ny\n42\n")

    assert read_env(tmp_path) == {
        "TELEGRAM_BOT_TOKEN": "123456:test-token",
        "DATABASE_PATH": "foodbot.local.sqlite3",
        "TELEGRAM_ADMIN_IDS": "42",
        "FOODBOT_TIMEZONE": "Europe/Belgrade",
        "SPLITWISE_API_KEY": "",
        "SPLITWISE_GROUP_ID": "",
    }
    assert "123456:test-token" not in result.stdout
    assert "123456:test-token" not in result.stderr


def test_setup_dev_keeps_existing_values_on_empty_answers(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "TELEGRAM_BOT_TOKEN=existing-token",
                "DATABASE_PATH=old.sqlite3",
                "TELEGRAM_ADMIN_IDS=42",
                "FOODBOT_TIMEZONE=UTC",
                "SPLITWISE_API_KEY=existing-splitwise-key",
                "SPLITWISE_GROUP_ID=1001",
            ]
        ),
        encoding="utf-8",
    )

    result = run_env_setup(tmp_path, "\n\n\n")

    assert read_env(tmp_path) == {
        "TELEGRAM_BOT_TOKEN": "existing-token",
        "DATABASE_PATH": "foodbot.local.sqlite3",
        "TELEGRAM_ADMIN_IDS": "42",
        "FOODBOT_TIMEZONE": "Europe/Belgrade",
        "SPLITWISE_API_KEY": "existing-splitwise-key",
        "SPLITWISE_GROUP_ID": "1001",
    }
    assert "existing-token" not in result.stdout
    assert "existing-token" not in result.stderr
    assert "Get the token from Telegram @BotFather" not in result.stdout


def test_setup_dev_reads_existing_env_with_export_spaces_and_quotes(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                'export TELEGRAM_BOT_TOKEN = "existing-token"',
                "DATABASE_PATH=old.sqlite3",
                "TELEGRAM_ADMIN_IDS = '42'",
                "FOODBOT_TIMEZONE=UTC",
                'SPLITWISE_API_KEY = "existing-splitwise-key"',
                "SPLITWISE_GROUP_ID = '1001'",
            ]
        ),
        encoding="utf-8",
    )

    result = run_env_setup(tmp_path, "\n\n\n")

    assert read_env(tmp_path) == {
        "TELEGRAM_BOT_TOKEN": "existing-token",
        "DATABASE_PATH": "foodbot.local.sqlite3",
        "TELEGRAM_ADMIN_IDS": "42",
        "FOODBOT_TIMEZONE": "Europe/Belgrade",
        "SPLITWISE_API_KEY": "existing-splitwise-key",
        "SPLITWISE_GROUP_ID": "1001",
    }
    assert "existing-token" not in result.stdout
    assert "existing-token" not in result.stderr
    assert "Get the token from Telegram @BotFather" not in result.stdout


def test_setup_dev_replaces_token_and_clears_admin_ids(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "TELEGRAM_BOT_TOKEN=old-token",
                "DATABASE_PATH=old.sqlite3",
                "TELEGRAM_ADMIN_IDS=42",
                "FOODBOT_TIMEZONE=UTC",
                "SPLITWISE_API_KEY=old-splitwise-key",
                "SPLITWISE_GROUP_ID=1001",
            ]
        ),
        encoding="utf-8",
    )

    result = run_env_setup(tmp_path, "new-token\nn\n")

    assert read_env(tmp_path) == {
        "TELEGRAM_BOT_TOKEN": "new-token",
        "DATABASE_PATH": "foodbot.local.sqlite3",
        "TELEGRAM_ADMIN_IDS": "",
        "FOODBOT_TIMEZONE": "Europe/Belgrade",
        "SPLITWISE_API_KEY": "old-splitwise-key",
        "SPLITWISE_GROUP_ID": "1001",
    }
    assert "old-token" not in result.stdout
    assert "old-token" not in result.stderr
    assert "new-token" not in result.stdout
    assert "new-token" not in result.stderr


def test_setup_dev_keeps_existing_env_when_interrupted_before_replace(tmp_path: Path) -> None:
    existing_env = "\n".join(
        [
            "TELEGRAM_BOT_TOKEN=old-token",
            "DATABASE_PATH=old.sqlite3",
            "TELEGRAM_ADMIN_IDS=42",
            "FOODBOT_TIMEZONE=UTC",
            "SPLITWISE_API_KEY=old-splitwise-key",
            "SPLITWISE_GROUP_ID=1001",
        ]
    )
    (tmp_path / ".env").write_text(existing_env, encoding="utf-8")

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_mv = fake_bin / "mv"
    fake_mv.write_text(
        "#!/usr/bin/env bash\n"
        'kill -INT "$PPID"\n'
        "sleep 1\n"
        "exit 130\n",
        encoding="utf-8",
    )
    fake_mv.chmod(0o755)

    result = subprocess.run(
        ["bash", str(SETUP_DEV), "--env-only", "--skip-token-check"],
        cwd=tmp_path,
        input="new-token\nn\n",
        text=True,
        capture_output=True,
        check=False,
        env={"PATH": f"{fake_bin}:{ROOT / '.venv' / 'bin'}:/usr/bin:/bin:/usr/sbin:/sbin"},
    )

    assert result.returncode == 130
    assert (tmp_path / ".env").read_text(encoding="utf-8") == existing_env
    assert not list(tmp_path.glob(".env.tmp.*"))
    assert "new-token" not in result.stdout
    assert "new-token" not in result.stderr


def test_setup_dev_reset_env_ignores_existing_values(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "TELEGRAM_BOT_TOKEN=old-token",
                "DATABASE_PATH=old.sqlite3",
                "TELEGRAM_ADMIN_IDS=42",
                "FOODBOT_TIMEZONE=UTC",
                "SPLITWISE_API_KEY=old-splitwise-key",
                "SPLITWISE_GROUP_ID=1001",
            ]
        ),
        encoding="utf-8",
    )

    result = run_env_setup(tmp_path, "fresh-token\nn\n", "--reset-env")

    assert read_env(tmp_path) == {
        "TELEGRAM_BOT_TOKEN": "fresh-token",
        "DATABASE_PATH": "foodbot.local.sqlite3",
        "TELEGRAM_ADMIN_IDS": "",
        "FOODBOT_TIMEZONE": "Europe/Belgrade",
        "SPLITWISE_API_KEY": "",
        "SPLITWISE_GROUP_ID": "",
    }
    assert "old-token" not in result.stdout
    assert "old-token" not in result.stderr
    assert "fresh-token" not in result.stdout
    assert "fresh-token" not in result.stderr


def test_setup_dev_rejects_invalid_token_without_skip(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(SETUP_DEV), "--env-only"],
        cwd=tmp_path,
        input="dummy-token\n",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "does not look like a real BotFather token" in result.stderr
    assert not (tmp_path / ".env").exists()


def test_setup_dev_verifies_valid_shape_token_without_extra_prompt(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(SETUP_DEV), "--env-only"],
        cwd=tmp_path,
        input="123456789:abcdefghijklmnopqrstuvwxyzABCDE\n",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Verify this bot token with Telegram now?" not in result.stdout
    assert "Continue with an unverified bot token?" not in result.stdout
    assert "Checking Telegram bot token..." in result.stdout
    assert not (tmp_path / ".env").exists()
