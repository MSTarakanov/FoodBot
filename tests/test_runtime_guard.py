from __future__ import annotations

import pytest

from office_food_bot import runtime_guard
from office_food_bot.config import RuntimeEnvironment, Settings
from office_food_bot.runtime_guard import (
    ProductionTokenInDevelopmentError,
    TelegramBotIdentity,
)


def make_settings(
    *,
    environment: RuntimeEnvironment = RuntimeEnvironment.DEVELOPMENT,
    production_telegram_bot_id: int | None = 8490386710,
) -> Settings:
    return Settings(
        environment=environment,
        telegram_bot_token="123456:test-token",
        database_path=":memory:",
        telegram_admin_ids=frozenset(),
        timezone="Europe/Belgrade",
        splitwise_api_key="splitwise-key",
        splitwise_group_id=43807503,
        production_telegram_bot_id=production_telegram_bot_id,
    )


async def test_runtime_guard_rejects_production_bot_in_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_fetch_telegram_bot_identity(bot: object) -> TelegramBotIdentity:
        return TelegramBotIdentity(
            telegram_bot_id=8490386710,
            username="jos_jedan_bot",
        )

    monkeypatch.setattr(
        runtime_guard,
        "fetch_telegram_bot_identity",
        fake_fetch_telegram_bot_identity,
    )

    with pytest.raises(ProductionTokenInDevelopmentError, match="production Telegram bot token"):
        await runtime_guard.ensure_safe_telegram_token_for_environment(
            make_settings(),
            object(),
        )


async def test_runtime_guard_allows_development_bot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_fetch_telegram_bot_identity(bot: object) -> TelegramBotIdentity:
        return TelegramBotIdentity(
            telegram_bot_id=123,
            username="foodbot_dev",
        )

    monkeypatch.setattr(
        runtime_guard,
        "fetch_telegram_bot_identity",
        fake_fetch_telegram_bot_identity,
    )

    await runtime_guard.ensure_safe_telegram_token_for_environment(
        make_settings(),
        object(),
    )


async def test_runtime_guard_skips_check_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_if_called(bot: object) -> TelegramBotIdentity:
        raise AssertionError("Production runtime should not validate against itself")

    monkeypatch.setattr(runtime_guard, "fetch_telegram_bot_identity", fail_if_called)

    await runtime_guard.ensure_safe_telegram_token_for_environment(
        make_settings(environment=RuntimeEnvironment.PRODUCTION),
        object(),
    )
