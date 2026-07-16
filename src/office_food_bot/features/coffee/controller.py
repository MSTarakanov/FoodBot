from __future__ import annotations

from aiogram import Bot
from aiogram.types import CallbackQuery

from office_food_bot.application.users.errors import ActiveUserErrorCode
from office_food_bot.application.users.resolver import ActiveUserResolver
from office_food_bot.commanding.errors.mapping import common_error_for_active_user
from office_food_bot.commanding.errors.models import CommonErrorCode
from office_food_bot.commanding.errors.rendering import (
    ErrorRenderer,
)
from office_food_bot.features.coffee.callbacks import CoffeeCallbackData
from office_food_bot.features.coffee.errors import CoffeeErrorCode
from office_food_bot.features.coffee.models import CoffeeParticipationReport
from office_food_bot.features.coffee.rendering import CoffeeCommandRenderer
from office_food_bot.features.coffee.service import CoffeeService
from office_food_bot.models import RegisteredUser


class CoffeeCallbackController:
    def __init__(
        self,
        coffee: CoffeeService,
        active_users: ActiveUserResolver,
        coffee_renderer: CoffeeCommandRenderer,
        common_error_renderer: ErrorRenderer[CommonErrorCode],
        error_renderer: ErrorRenderer[CoffeeErrorCode],
    ) -> None:
        self._coffee = coffee
        self._active_users = active_users
        self._coffee_renderer = coffee_renderer
        self._common_error_renderer = common_error_renderer
        self._error_renderer = error_renderer

    async def handle(
        self,
        callback_query: CallbackQuery,
        bot: Bot,
    ) -> None:
        callback_data = CoffeeCallbackData.unpack(callback_query.data or "")
        if callback_data is None:
            await self._answer_coffee_error(
                callback_query,
                CoffeeErrorCode.INVALID_CALLBACK,
            )
            return
        await self._active_users.resolve(callback_query.from_user.id).fold(
            lambda user: self._update_participation(
                callback_query,
                bot,
                user,
                callback_data,
            ),
            lambda code: self._answer_active_user_error(callback_query, code),
        )

    async def _answer_active_user_error(
        self,
        callback_query: CallbackQuery,
        code: ActiveUserErrorCode,
    ) -> None:
        await self._answer_common_error(
            callback_query,
            common_error_for_active_user(code),
        )

    async def _update_participation(
        self,
        callback_query: CallbackQuery,
        bot: Bot,
        user: RegisteredUser,
        callback_data: CoffeeCallbackData,
    ) -> None:
        result = await self._coffee.update_participation(bot, user, callback_data)
        await result.fold(
            lambda report: self._answer_success(callback_query, report),
            lambda code: self._answer_coffee_error(callback_query, code),
        )

    async def _answer_success(
        self,
        callback_query: CallbackQuery,
        report: CoffeeParticipationReport,
    ) -> None:
        await callback_query.answer(
            self._coffee_renderer.participation(report),
            show_alert=False,
        )

    async def _answer_common_error(
        self,
        callback_query: CallbackQuery,
        code: CommonErrorCode,
    ) -> None:
        await callback_query.answer(
            self._common_error_renderer.render(code),
            show_alert=True,
        )

    async def _answer_coffee_error(
        self,
        callback_query: CallbackQuery,
        code: CoffeeErrorCode,
    ) -> None:
        await callback_query.answer(
            self._error_renderer.render(code),
            show_alert=True,
        )
