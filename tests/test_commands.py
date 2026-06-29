from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import TelegramMethod
from aiogram.methods.send_message import SendMessage
from aiogram.types import Chat, Message, Update, User

from office_food_bot.app import create_dispatcher


class RecordingSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.requests: list[TelegramMethod[Any]] = []

    async def close(self) -> None:
        return None

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[Any],
        timeout: int | None = None,
    ) -> Message:
        self.requests.append(method)
        if isinstance(method, SendMessage):
            return Message(
                message_id=len(self.requests),
                date=datetime.now(tz=UTC),
                chat=Chat(id=method.chat_id, type="private"),
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
    ) -> Any:
        raise AssertionError("No streaming calls are expected in command tests")


def make_update(text: str) -> Update:
    user = User(id=42, is_bot=False, first_name="Misha", username="misha")
    chat = Chat(id=42, type="private")
    message = Message(
        message_id=100,
        date=datetime.now(tz=UTC),
        chat=chat,
        from_user=user,
        text=text,
    )
    return Update(update_id=1, message=message)


@pytest.mark.parametrize(
    ("incoming_text", "expected_text"),
    [
        ("/start", "Привет! Я офисный бот про еду. Пока умею команды /start и /hi."),
        ("/hi", "Привет! Я на месте."),
    ],
)
async def test_commands_reply_with_expected_text(
    incoming_text: str,
    expected_text: str,
) -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = create_dispatcher()

    await dispatcher.feed_update(bot, make_update(incoming_text))

    assert len(session.requests) == 1
    request = session.requests[0]
    assert isinstance(request, SendMessage)
    assert request.chat_id == 42
    assert request.text == expected_text
