from __future__ import annotations

from aiogram import Bot
from aiogram.types import CallbackQuery

from office_food_bot.coffee_callbacks import CoffeeCallbackData
from office_food_bot.services import BotServices


async def coffee_callback_handler(
    callback_query: CallbackQuery,
    bot: Bot,
    services: BotServices,
) -> None:
    callback_data = CoffeeCallbackData.unpack(callback_query.data or "")
    if callback_data is None:
        await callback_query.answer("Не понял действие.", show_alert=True)
        return
    result = await services.coffee.update_participation(
        bot,
        callback_query.from_user.id,
        callback_data,
    )
    await callback_query.answer(result.text, show_alert=result.show_alert)
