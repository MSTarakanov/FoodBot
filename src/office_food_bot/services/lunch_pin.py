from __future__ import annotations

from datetime import date

from aiogram import Bot

from office_food_bot.messaging import BotMessenger
from office_food_bot.repositories import LunchPinRepository


class LunchPinService:
    def __init__(
        self,
        messenger: BotMessenger,
        pins: LunchPinRepository,
    ) -> None:
        self._messenger = messenger
        self._pins = pins

    async def replace_pin(
        self,
        bot: Bot,
        chat_id: int,
        new_message_id: int,
        lunch_date: date,
    ) -> None:
        existing_pin = self._pins.get(chat_id)
        if existing_pin is not None and existing_pin.message_id != new_message_id:
            await self._messenger.try_unpin_chat_message(
                bot,
                chat_id,
                existing_pin.message_id,
            )

        pinned = await self._messenger.try_pin_chat_message(
            bot,
            chat_id,
            new_message_id,
        )
        if pinned:
            self._pins.upsert(chat_id, new_message_id, lunch_date)

    async def clear_saved_pin(self, bot: Bot, chat_id: int) -> None:
        existing_pin = self._pins.get(chat_id)
        if existing_pin is None:
            return

        await self._messenger.try_unpin_chat_message(
            bot,
            chat_id,
            existing_pin.message_id,
        )
        self._pins.clear(chat_id)
