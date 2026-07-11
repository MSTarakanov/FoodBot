from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import (
    EditMessageText,
    PinChatMessage,
    SendMessage,
    SendPoll,
    TelegramMethod,
    UnpinChatMessage,
)
from aiogram.types import Chat, Message, ReplyKeyboardRemove

from office_food_bot.messaging import BotMessenger, InlineChoice


class RecordingSession(BaseSession):
    def __init__(self, fail_method_name: str | None = None) -> None:
        super().__init__()
        self._fail_method_name = fail_method_name
        self.requests: list[TelegramMethod[Any]] = []

    async def close(self) -> None:
        return None

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[Any],
        timeout: int | None = None,
    ) -> Message:
        if type(method).__name__ == self._fail_method_name:
            raise TelegramBadRequest(method=method, message="Bad Request")

        self.requests.append(method)
        if isinstance(method, PinChatMessage | UnpinChatMessage):
            return True
        if isinstance(method, EditMessageText):
            return Message(
                message_id=method.message_id or 1,
                date=datetime.now(tz=UTC),
                chat=Chat(id=42, type="private"),
            )
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


async def test_try_pin_chat_message_uses_silent_pin() -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    messenger = BotMessenger()

    pinned = await messenger.try_pin_chat_message(bot, 42, 100)

    method = session.requests[0]
    assert pinned
    assert isinstance(method, PinChatMessage)
    assert method.chat_id == 42
    assert method.message_id == 100
    assert method.disable_notification is True


async def test_edit_or_send_edits_existing_message() -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)

    message = await BotMessenger().edit_or_send(bot, 42, 100, "Новое время")

    assert message.message_id == 100
    assert len(session.requests) == 1
    assert isinstance(session.requests[0], EditMessageText)


async def test_edit_or_send_falls_back_to_new_message() -> None:
    session = RecordingSession(fail_method_name="EditMessageText")
    bot = Bot(token="123456:test-token", session=session)

    message = await BotMessenger().edit_or_send(bot, 42, 100, "Новая карточка")

    assert message.message_id == 1
    assert len(session.requests) == 1
    assert isinstance(session.requests[0], SendMessage)


async def test_try_unpin_chat_message_uses_message_id() -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    messenger = BotMessenger()

    unpinned = await messenger.try_unpin_chat_message(bot, 42, 100)

    method = session.requests[0]
    assert unpinned
    assert isinstance(method, UnpinChatMessage)
    assert method.chat_id == 42
    assert method.message_id == 100


async def test_try_pin_and_unpin_return_false_on_telegram_error() -> None:
    pin_session = RecordingSession(fail_method_name="PinChatMessage")
    unpin_session = RecordingSession(fail_method_name="UnpinChatMessage")
    messenger = BotMessenger()

    pinned = await messenger.try_pin_chat_message(
        Bot(token="123456:test-token", session=pin_session),
        42,
        100,
    )
    unpinned = await messenger.try_unpin_chat_message(
        Bot(token="123456:test-token", session=unpin_session),
        42,
        100,
    )

    assert not pinned
    assert not unpinned


def test_remove_keyboard_markup() -> None:
    markup = BotMessenger().remove_keyboard()

    assert isinstance(markup, ReplyKeyboardRemove)
    assert markup.remove_keyboard is True
