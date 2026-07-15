from __future__ import annotations

from aiogram import F, Router

from office_food_bot.commanding.catalog import CommandCatalog
from office_food_bot.commanding.dispatcher import CommandDispatcher
from office_food_bot.commanding.errors.middleware import UserFacingErrorMiddleware
from office_food_bot.commanding.errors.rendering import UserErrorRenderer
from office_food_bot.controllers.coffee import coffee_callback_handler
from office_food_bot.controllers.polls import poll_answer_handler
from office_food_bot.flows.runner import ActiveFlowState, FlowRunner
from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices


def create_command_router(
    services: BotServices,
    messenger: BotMessenger,
    catalog: CommandCatalog,
    error_renderer: UserErrorRenderer,
    flow_runner: FlowRunner,
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
        flow_runner,
    )
    router.message.register(
        command_dispatcher.dispatch,
        F.text.startswith("/"),
    )
    router.callback_query.register(coffee_callback_handler, F.data.startswith("coffee:"))
    router.poll_answer.register(poll_answer_handler)
    router.message.register(flow_runner.handle_message, ActiveFlowState.active)
    return router
