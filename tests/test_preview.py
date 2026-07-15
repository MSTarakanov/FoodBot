from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import GetMe, SendMessage, TelegramMethod
from aiogram.methods.base import TelegramType
from aiogram.types import Chat, Message, User

from office_food_bot.config import RuntimeEnvironment, Settings
from office_food_bot.messaging import TextMessagePayload
from office_food_bot.preview import PreviewError, deliver_preview, resolve_chat_id
from office_food_bot.previews import MESSAGE_PREVIEWS


class PreviewSession(BaseSession):
    def __init__(self, failure: str | None = None) -> None:
        super().__init__()
        self.failure = failure
        self.sent_messages: list[SendMessage] = []

    async def close(self) -> None:
        return None

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int | None = None,
    ) -> TelegramType:
        if isinstance(method, GetMe):
            return User(
                id=123456,
                is_bot=True,
                first_name="FoodBot Preview",
                username="foodbot_dev",
            )
        if isinstance(method, SendMessage):
            if self.failure == "forbidden":
                raise TelegramForbiddenError(
                    method=method,
                    message="Forbidden: bot can't initiate conversation with a user",
                )
            if self.failure == "chat-not-found":
                raise TelegramBadRequest(method=method, message="Bad Request: chat not found")
            self.sent_messages.append(method)
            return Message(
                message_id=1,
                date=datetime.now(tz=UTC),
                chat=Chat(id=int(method.chat_id), type="private"),
                text=method.text,
            )
        raise AssertionError(f"Unexpected Telegram method: {type(method).__name__}")

    async def stream_content(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes]:
        raise AssertionError("No streaming calls are expected in preview tests")
        yield b""


def make_settings(
    *,
    environment: RuntimeEnvironment = RuntimeEnvironment.DEVELOPMENT,
    admin_ids: frozenset[int] = frozenset({42}),
) -> Settings:
    return Settings(
        environment=environment,
        telegram_bot_token="123456:test-token",
        telegram_bot_username="foodbot_dev",
        database_path="test.sqlite3",
        telegram_admin_ids=admin_ids,
        timezone="Europe/Belgrade",
        splitwise_api_key=None,
        splitwise_group_id=55,
        production_telegram_bot_id=8490386710,
    )


def test_resolve_chat_id_uses_the_only_admin() -> None:
    assert resolve_chat_id(make_settings(), None) == 42


def test_resolve_chat_id_prefers_explicit_value() -> None:
    assert resolve_chat_id(make_settings(admin_ids=frozenset({42, 43})), 99) == 99


def test_resolve_chat_id_requires_configured_admin_or_override() -> None:
    with pytest.raises(PreviewError, match="TELEGRAM_ADMIN_IDS is empty"):
        resolve_chat_id(make_settings(admin_ids=frozenset()), None)


def test_resolve_chat_id_requires_override_for_multiple_admins() -> None:
    with pytest.raises(PreviewError, match="Multiple TELEGRAM_ADMIN_IDS"):
        resolve_chat_id(make_settings(admin_ids=frozenset({42, 43})), None)


async def test_deliver_preview_sends_catalog_payload() -> None:
    session = PreviewSession()
    bot = Bot(token="123456:test-token", session=session)

    await deliver_preview(make_settings(), "balance-full", 42, bot=bot)

    expected = MESSAGE_PREVIEWS.render("balance-full")
    assert isinstance(expected, TextMessagePayload)
    assert len(session.sent_messages) == 1
    assert session.sent_messages[0].text == expected.text
    assert session.sent_messages[0].parse_mode == expected.parse_mode
    assert session.sent_messages[0].link_preview_options == expected.link_preview_options


async def test_deliver_preview_rejects_production_environment() -> None:
    with pytest.raises(PreviewError, match="only works with FOODBOT_ENV=development"):
        await deliver_preview(
            make_settings(environment=RuntimeEnvironment.PRODUCTION),
            "balance-full",
            42,
            bot=Bot(token="123456:test-token", session=PreviewSession()),
        )


async def test_deliver_preview_rejects_unknown_case() -> None:
    with pytest.raises(PreviewError, match="Unknown preview case: unknown"):
        await deliver_preview(
            make_settings(),
            "unknown",
            42,
            bot=Bot(token="123456:test-token", session=PreviewSession()),
        )


@pytest.mark.parametrize("failure", ["forbidden", "chat-not-found"])
async def test_deliver_preview_explains_that_user_must_start_bot(failure: str) -> None:
    bot = Bot(token="123456:test-token", session=PreviewSession(failure))

    with pytest.raises(PreviewError, match="https://t.me/foodbot_dev") as error:
        await deliver_preview(make_settings(), "balance-full", 42, bot=bot)

    assert "press Start" in str(error.value)
