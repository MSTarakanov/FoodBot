from __future__ import annotations

from pathlib import Path

import pytest

from office_food_bot.config import load_settings


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "TELEGRAM_BOT_TOKEN",
        "DATABASE_PATH",
        "TELEGRAM_ADMIN_IDS",
        "FOODBOT_TIMEZONE",
        "SPLITWISE_API_KEY",
        "SPLITWISE_GROUP_ID",
    ):
        monkeypatch.delenv(name, raising=False)


def test_load_settings_uses_defaults_and_local_overrides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.defaults").write_text(
        "\n".join(
            [
                "DATABASE_PATH=default.sqlite3",
                "TELEGRAM_ADMIN_IDS=1,2",
                "FOODBOT_TIMEZONE=UTC",
                "SPLITWISE_GROUP_ID=1001",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "TELEGRAM_BOT_TOKEN=123456:test-token",
                "TELEGRAM_ADMIN_IDS=3",
                "SPLITWISE_API_KEY=splitwise-dev-key",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_settings()

    assert settings.telegram_bot_token == "123456:test-token"
    assert settings.database_path == "default.sqlite3"
    assert settings.telegram_admin_ids == frozenset({3})
    assert settings.timezone == "UTC"
    assert settings.splitwise_api_key == "splitwise-dev-key"
    assert settings.splitwise_group_id == 1001


def test_environment_variables_have_highest_priority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.defaults").write_text(
        "\n".join(
            [
                "TELEGRAM_BOT_TOKEN=from-defaults",
                "DATABASE_PATH=default.sqlite3",
                "TELEGRAM_ADMIN_IDS=1",
                "FOODBOT_TIMEZONE=UTC",
                "SPLITWISE_GROUP_ID=1001",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text("TELEGRAM_BOT_TOKEN=from-local\n")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "from-process")
    monkeypatch.setenv("DATABASE_PATH", "process.sqlite3")
    monkeypatch.setenv("SPLITWISE_GROUP_ID", "2002")

    settings = load_settings()

    assert settings.telegram_bot_token == "from-process"
    assert settings.database_path == "process.sqlite3"
    assert settings.telegram_admin_ids == frozenset({1})
    assert settings.timezone == "UTC"
    assert settings.splitwise_group_id == 2002


def test_load_settings_fails_when_required_config_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "TELEGRAM_BOT_TOKEN=123456:test-token",
                "TELEGRAM_ADMIN_IDS=",
                "FOODBOT_TIMEZONE=UTC",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="DATABASE_PATH environment variable is required"):
        load_settings()


def test_load_settings_rejects_invalid_splitwise_group_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "TELEGRAM_BOT_TOKEN=123456:test-token",
                "DATABASE_PATH=foodbot.sqlite3",
                "TELEGRAM_ADMIN_IDS=",
                "FOODBOT_TIMEZONE=UTC",
                "SPLITWISE_GROUP_ID=not-a-number",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="SPLITWISE_GROUP_ID must be an integer"):
        load_settings()
