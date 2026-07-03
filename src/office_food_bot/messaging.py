from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputPollOption,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)


@dataclass(frozen=True, slots=True)
class InlineChoice:
    text: str
    callback_data: str


class BotMessenger:
    async def reply(self, message: Message, text: str, **kwargs: Any) -> Message:
        return await message.answer(text, **kwargs)

    async def send(self, bot: Bot, chat_id: int, text: str, **kwargs: Any) -> Message:
        return await bot.send_message(chat_id, text, **kwargs)

    async def reply_with_choices(
        self,
        message: Message,
        text: str,
        choices: Sequence[str],
        *,
        columns: int = 2,
        one_time_keyboard: bool = True,
        **kwargs: Any,
    ) -> Message:
        return await self.reply(
            message,
            text,
            reply_markup=self.choice_keyboard(
                choices,
                columns=columns,
                one_time_keyboard=one_time_keyboard,
            ),
            **kwargs,
        )

    async def send_with_choices(
        self,
        bot: Bot,
        chat_id: int,
        text: str,
        choices: Sequence[str],
        *,
        columns: int = 2,
        one_time_keyboard: bool = True,
        **kwargs: Any,
    ) -> Message:
        return await self.send(
            bot,
            chat_id,
            text,
            reply_markup=self.choice_keyboard(
                choices,
                columns=columns,
                one_time_keyboard=one_time_keyboard,
            ),
            **kwargs,
        )

    async def reply_with_inline_choices(
        self,
        message: Message,
        text: str,
        choices: Sequence[InlineChoice],
        *,
        columns: int = 2,
        **kwargs: Any,
    ) -> Message:
        return await self.reply(
            message,
            text,
            reply_markup=self.inline_keyboard(choices, columns=columns),
            **kwargs,
        )

    async def send_with_inline_choices(
        self,
        bot: Bot,
        chat_id: int,
        text: str,
        choices: Sequence[InlineChoice],
        *,
        columns: int = 2,
        **kwargs: Any,
    ) -> Message:
        return await self.send(
            bot,
            chat_id,
            text,
            reply_markup=self.inline_keyboard(choices, columns=columns),
            **kwargs,
        )

    async def reply_poll(
        self,
        message: Message,
        question: str,
        options: Sequence[str],
        **kwargs: Any,
    ) -> Message:
        return await message.answer_poll(question, _poll_options(options), **kwargs)

    async def send_poll(
        self,
        bot: Bot,
        chat_id: int,
        question: str,
        options: Sequence[str],
        **kwargs: Any,
    ) -> Message:
        return await bot.send_poll(chat_id, question, _poll_options(options), **kwargs)

    async def try_send(self, bot: Bot, chat_id: int, text: str, **kwargs: Any) -> bool:
        try:
            await self.send(bot, chat_id, text, **kwargs)
        except TelegramAPIError:
            return False
        return True

    async def try_send_poll(
        self,
        bot: Bot,
        chat_id: int,
        question: str,
        options: Sequence[str],
        **kwargs: Any,
    ) -> bool:
        try:
            await self.send_poll(bot, chat_id, question, options, **kwargs)
        except TelegramAPIError:
            return False
        return True

    def choice_keyboard(
        self,
        choices: Sequence[str],
        *,
        columns: int = 2,
        one_time_keyboard: bool = True,
        resize_keyboard: bool = True,
    ) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=choice) for choice in row]
                for row in _chunked(_text_options(choices, minimum=1), columns)
            ],
            resize_keyboard=resize_keyboard,
            one_time_keyboard=one_time_keyboard,
        )

    def inline_keyboard(
        self,
        choices: Sequence[InlineChoice],
        *,
        columns: int = 2,
    ) -> InlineKeyboardMarkup:
        if not choices:
            msg = "At least one inline choice is required"
            raise ValueError(msg)

        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=choice.text,
                        callback_data=choice.callback_data,
                    )
                    for choice in row
                ]
                for row in _chunked(tuple(choices), columns)
            ],
        )

    def remove_keyboard(self) -> ReplyKeyboardRemove:
        return ReplyKeyboardRemove(remove_keyboard=True)


def _poll_options(options: Sequence[str]) -> list[InputPollOption | str]:
    return [
        InputPollOption(text=option)
        for option in _text_options(options, minimum=2, maximum=10)
    ]


def _text_options(
    options: Sequence[str],
    *,
    minimum: int,
    maximum: int | None = None,
) -> tuple[str, ...]:
    cleaned_options = tuple(option.strip() for option in options)
    if any(not option for option in cleaned_options):
        msg = "Options must not contain blank values"
        raise ValueError(msg)
    if len(cleaned_options) < minimum:
        msg = f"At least {minimum} options are required"
        raise ValueError(msg)
    if maximum is not None and len(cleaned_options) > maximum:
        msg = f"No more than {maximum} options are allowed"
        raise ValueError(msg)
    return cleaned_options


def _chunked[T](values: Sequence[T], columns: int) -> tuple[tuple[T, ...], ...]:
    if columns < 1:
        msg = "columns must be greater than zero"
        raise ValueError(msg)

    return tuple(
        tuple(values[index : index + columns])
        for index in range(0, len(values), columns)
    )
