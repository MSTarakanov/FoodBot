from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import SendMessage, SendPoll, TelegramMethod
from aiogram.types import Chat, Message, ReplyKeyboardRemove

from office_food_bot.messaging import BotMessenger, InlineChoice


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
        return Message(
            message_id=len(self.requests),
            date=datetime.now(tz=UTC),
            chat=Chat(id=42, type="private"),
        )

    async def stream_content(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes]:
        raise AssertionError("No streaming calls are expected in messenger tests")
        yield b""


async def test_send_with_choices_uses_reply_keyboard() -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    messenger = BotMessenger()

    await messenger.send_with_choices(bot, 42, "Выбери вариант", ["Да", "Нет"])

    method = session.requests[0]
    assert isinstance(method, SendMessage)
    assert method.text == "Выбери вариант"
    assert method.reply_markup is not None
    assert [
        [button.text for button in row]
        for row in method.reply_markup.keyboard
    ] == [["Да", "Нет"]]
    assert method.reply_markup.one_time_keyboard is True


async def test_send_with_inline_choices_uses_callback_buttons() -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    messenger = BotMessenger()

    await messenger.send_with_inline_choices(
        bot,
        42,
        "Подтвердить?",
        [
            InlineChoice(text="Да", callback_data="confirm:yes"),
            InlineChoice(text="Нет", callback_data="confirm:no"),
        ],
        columns=1,
    )

    method = session.requests[0]
    assert isinstance(method, SendMessage)
    assert method.reply_markup is not None
    assert [
        [(button.text, button.callback_data) for button in row]
        for row in method.reply_markup.inline_keyboard
    ] == [[("Да", "confirm:yes")], [("Нет", "confirm:no")]]


async def test_send_poll_uses_telegram_poll_options() -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    messenger = BotMessenger()

    await messenger.send_poll(
        bot,
        42,
        "Что заказать?",
        ["Пицца", "Суши"],
        is_anonymous=False,
        allows_multiple_answers=True,
    )

    method = session.requests[0]
    assert isinstance(method, SendPoll)
    assert method.question == "Что заказать?"
    assert [option.text for option in method.options] == ["Пицца", "Суши"]
    assert method.is_anonymous is False
    assert method.allows_multiple_answers is True


async def test_send_poll_validates_options_before_calling_telegram() -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    messenger = BotMessenger()

    with pytest.raises(ValueError, match="At least 2 options"):
        await messenger.send_poll(bot, 42, "Что заказать?", ["Пицца"])

    assert session.requests == []


def test_remove_keyboard_markup() -> None:
    markup = BotMessenger().remove_keyboard()

    assert isinstance(markup, ReplyKeyboardRemove)
    assert markup.remove_keyboard is True
