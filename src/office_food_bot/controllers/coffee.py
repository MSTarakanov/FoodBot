from __future__ import annotations

from aiogram import Bot
from aiogram.types import CallbackQuery

from office_food_bot.coffee_callbacks import CoffeeCallbackData
from office_food_bot.commanding.errors.models import (
    CoffeeError,
    CoffeeErrorCode,
    UserFacingError,
)
from office_food_bot.commanding.errors.rendering import (
    ErrorRenderer,
)
from office_food_bot.presenters.coffee import CoffeeCommandRenderer
from office_food_bot.services.coffee import CoffeeService


class CoffeeCallbackController:
    def __init__(
        self,
        coffee: CoffeeService,
        coffee_renderer: CoffeeCommandRenderer,
        error_renderer: ErrorRenderer,
    ) -> None:
        self._coffee = coffee
        self._coffee_renderer = coffee_renderer
        self._error_renderer = error_renderer

    async def handle(
        self,
        callback_query: CallbackQuery,
        bot: Bot,
    ) -> None:
        try:
            callback_data = CoffeeCallbackData.unpack(callback_query.data or "")
            if callback_data is None:
                raise CoffeeError(CoffeeErrorCode.INVALID_CALLBACK)
            result = await self._coffee.update_participation(
                bot,
                callback_query.from_user.id,
                callback_data,
            )
        except UserFacingError as error:
            await callback_query.answer(
                self._error_renderer.render(error),
                show_alert=True,
            )
            return
        await callback_query.answer(
            self._coffee_renderer.participation(result),
            show_alert=False,
        )
