from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputPollOption,
    InputPollOptionUnion,
    KeyboardButton,
    LinkPreviewOptions,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    ReplyMarkupUnion,
    ReplyParameters,
)

from office_food_bot.poll_options import PollOption


@dataclass(frozen=True, slots=True)
class InlineChoice:
    text: str
    callback_data: str


@dataclass(frozen=True, slots=True)
class LiveMessageReference:
    message_id: int


EDIT_TARGET_UNAVAILABLE_MESSAGES = (
    "message to edit not found",
    "message can't be edited",
)


class BotMessenger:
    async def reply(
        self,
        message: Message,
        text: str,
        *,
        reply_markup: ReplyMarkupUnion | None = None,
        parse_mode: ParseMode | None = None,
        link_preview_options: LinkPreviewOptions | None = None,
    ) -> Message:
        return await message.answer(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            link_preview_options=link_preview_options,
        )

    async def send(
        self,
        bot: Bot,
        chat_id: int,
        text: str,
        *,
        reply_markup: ReplyMarkupUnion | None = None,
        reply_to_message_id: int | None = None,
        parse_mode: ParseMode | None = None,
    ) -> Message:
        reply_parameters = None
        if reply_to_message_id is not None:
            reply_parameters = ReplyParameters(message_id=reply_to_message_id)
        return await bot.send_message(
            chat_id,
            text,
            reply_markup=reply_markup,
            reply_parameters=reply_parameters,
            parse_mode=parse_mode,
        )

    async def edit_or_send(
        self,
        bot: Bot,
        chat_id: int,
        message_id: int | None,
        text: str,
        *,
        reply_markup: InlineKeyboardMarkup | None = None,
        parse_mode: ParseMode | None = None,
    ) -> LiveMessageReference:
        if message_id is not None:
            try:
                edited = await bot.edit_message_text(
                    text=text,
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                )
                if isinstance(edited, Message):
                    return LiveMessageReference(edited.message_id)
                return LiveMessageReference(message_id)
            except TelegramBadRequest as error:
                if "message is not modified" in str(error).casefold():
                    return LiveMessageReference(message_id)
                if not _is_edit_target_unavailable(error):
                    raise
        sent = await self.send(
            bot,
            chat_id,
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        return LiveMessageReference(sent.message_id)

    async def try_edit_message(
        self,
        bot: Bot,
        chat_id: int,
        message_id: int,
        text: str,
        *,
        parse_mode: ParseMode | None = None,
    ) -> bool:
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=None,
                parse_mode=parse_mode,
            )
        except TelegramAPIError:
            return False
        return True

    async def reply_with_choices(
        self,
        message: Message,
        text: str,
        choices: Sequence[str],
        *,
        columns: int = 2,
        one_time_keyboard: bool = True,
    ) -> Message:
        return await self.reply(
            message,
            text,
            reply_markup=self.choice_keyboard(
                choices,
                columns=columns,
                one_time_keyboard=one_time_keyboard,
            ),
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
        )

    async def reply_with_inline_choices(
        self,
        message: Message,
        text: str,
        choices: Sequence[InlineChoice],
        *,
        columns: int = 2,
    ) -> Message:
        return await self.reply(
            message,
            text,
            reply_markup=self.inline_keyboard(choices, columns=columns),
        )

    async def send_with_inline_choices(
        self,
        bot: Bot,
        chat_id: int,
        text: str,
        choices: Sequence[InlineChoice],
        *,
        columns: int = 2,
    ) -> Message:
        return await self.send(
            bot,
            chat_id,
            text,
            reply_markup=self.inline_keyboard(choices, columns=columns),
        )

    async def reply_poll(
        self,
        message: Message,
        question: str,
        options: Sequence[PollOption],
        *,
        is_anonymous: bool = True,
        allows_multiple_answers: bool = False,
        allow_adding_options: bool = False,
    ) -> Message:
        return await message.answer_poll(
            question,
            _poll_options(options),
            is_anonymous=is_anonymous,
            allows_multiple_answers=allows_multiple_answers,
            allow_adding_options=allow_adding_options,
        )

    async def send_poll(
        self,
        bot: Bot,
        chat_id: int,
        question: str,
        options: Sequence[PollOption],
        *,
        is_anonymous: bool = True,
        allows_multiple_answers: bool = False,
        allow_adding_options: bool = False,
    ) -> Message:
        return await bot.send_poll(
            chat_id,
            question,
            _poll_options(options),
            is_anonymous=is_anonymous,
            allows_multiple_answers=allows_multiple_answers,
            allow_adding_options=allow_adding_options,
        )

    async def try_send(
        self,
        bot: Bot,
        chat_id: int,
        text: str,
        *,
        reply_markup: ReplyMarkupUnion | None = None,
        reply_to_message_id: int | None = None,
    ) -> bool:
        try:
            await self.send(
                bot,
                chat_id,
                text,
                reply_markup=reply_markup,
                reply_to_message_id=reply_to_message_id,
            )
        except TelegramAPIError:
            return False
        return True

    async def try_send_poll(
        self,
        bot: Bot,
        chat_id: int,
        question: str,
        options: Sequence[PollOption],
        *,
        is_anonymous: bool = True,
        allows_multiple_answers: bool = False,
        allow_adding_options: bool = False,
    ) -> bool:
        try:
            await self.send_poll(
                bot,
                chat_id,
                question,
                options,
                is_anonymous=is_anonymous,
                allows_multiple_answers=allows_multiple_answers,
                allow_adding_options=allow_adding_options,
            )
        except TelegramAPIError:
            return False
        return True

    async def try_pin_chat_message(
        self,
        bot: Bot,
        chat_id: int,
        message_id: int,
    ) -> bool:
        try:
            await bot.pin_chat_message(
                chat_id=chat_id,
                message_id=message_id,
                disable_notification=True,
            )
        except TelegramAPIError:
            return False
        return True

    async def try_unpin_chat_message(
        self,
        bot: Bot,
        chat_id: int,
        message_id: int,
    ) -> bool:
        try:
            await bot.unpin_chat_message(
                chat_id=chat_id,
                message_id=message_id,
            )
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


def _poll_options(options: Sequence[PollOption]) -> list[InputPollOptionUnion]:
    display_values = _text_options(
        tuple(option.display_value for option in options),
        minimum=2,
        maximum=10,
    )
    return [
        InputPollOption(text=display_value)
        for display_value in display_values
    ]


def _is_edit_target_unavailable(error: TelegramBadRequest) -> bool:
    error_text = str(error).casefold()
    return any(
        message in error_text
        for message in EDIT_TARGET_UNAVAILABLE_MESSAGES
    )


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
