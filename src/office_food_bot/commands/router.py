from __future__ import annotations

from aiogram import F, Router

from office_food_bot.commands.catalog import CommandCatalog
from office_food_bot.commands.coffee import coffee_callback_handler
from office_food_bot.commands.dispatcher import CommandDispatcher
from office_food_bot.commands.error_middleware import UserFacingErrorMiddleware
from office_food_bot.commands.error_rendering import UserErrorRenderer
from office_food_bot.commands.poll_tracking import poll_answer_handler
from office_food_bot.commands.register import (
    RegistrationFlow,
    confirm_reregistration_message,
    confirm_reregistration_unknown_message,
    register_coffee_preference_message,
    register_lunch_preference_message,
    register_name_message,
    register_splitwise_email_message,
    registration_waiting_for_coffee_preference_unknown_message,
    registration_waiting_for_lunch_preference_unknown_message,
    registration_waiting_for_name_unknown_message,
    registration_waiting_for_splitwise_unknown_message,
)
from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices


def create_command_router(
    services: BotServices,
    messenger: BotMessenger,
    catalog: CommandCatalog,
    error_renderer: UserErrorRenderer,
) -> Router:
    router = Router(name="commands")
    router.message.outer_middleware(
        UserFacingErrorMiddleware(
            catalog,
            error_renderer,
            messenger,
            services.telegram_bot_username,
        )
    )
    command_dispatcher = CommandDispatcher(
        catalog,
        services.command_access,
        messenger,
        services.telegram_bot_username,
    )
    router.message.register(
        command_dispatcher.dispatch,
        F.text.startswith("/"),
    )
    router.callback_query.register(coffee_callback_handler, F.data.startswith("coffee:"))
    router.poll_answer.register(poll_answer_handler)
    router.message.register(register_name_message, RegistrationFlow.waiting_for_name, F.text)
    router.message.register(
        register_splitwise_email_message,
        RegistrationFlow.waiting_for_splitwise_email,
        F.text,
    )
    router.message.register(
        register_lunch_preference_message,
        RegistrationFlow.waiting_for_lunch_preference,
        F.text,
    )
    router.message.register(
        register_coffee_preference_message,
        RegistrationFlow.waiting_for_coffee_preference,
        F.text,
    )
    router.message.register(
        confirm_reregistration_message,
        RegistrationFlow.confirming_reregistration,
        F.text,
    )
    router.message.register(
        confirm_reregistration_unknown_message,
        RegistrationFlow.confirming_reregistration,
    )
    router.message.register(
        registration_waiting_for_name_unknown_message,
        RegistrationFlow.waiting_for_name,
    )
    router.message.register(
        registration_waiting_for_splitwise_unknown_message,
        RegistrationFlow.waiting_for_splitwise_email,
    )
    router.message.register(
        registration_waiting_for_lunch_preference_unknown_message,
        RegistrationFlow.waiting_for_lunch_preference,
    )
    router.message.register(
        registration_waiting_for_coffee_preference_unknown_message,
        RegistrationFlow.waiting_for_coffee_preference,
    )
    return router
