from __future__ import annotations

from aiogram import F, Router

from office_food_bot.commanding.catalog import CommandCatalog
from office_food_bot.commanding.dispatcher import CommandDispatcher
from office_food_bot.commanding.errors.middleware import UserFacingErrorMiddleware
from office_food_bot.commanding.errors.rendering import (
    BotUsernameErrorRenderer,
    CallbackErrorRenderer,
    ErrorRenderer,
)
from office_food_bot.controllers.coffee import CoffeeCallbackController
from office_food_bot.controllers.polls import PollAnswerController
from office_food_bot.flows.runner import ActiveFlowState, FlowRunner
from office_food_bot.presenters.coffee import CoffeeCommandRenderer
from office_food_bot.services import BotServices


def create_command_router(
    services: BotServices,
    catalog: CommandCatalog,
    error_renderer: ErrorRenderer,
    flow_runner: FlowRunner,
) -> Router:
    messenger = services.messenger
    router = Router(name="commands")
    router.message.outer_middleware(
        UserFacingErrorMiddleware(
            catalog,
            BotUsernameErrorRenderer(
                error_renderer,
                services.telegram_bot_username,
            ),
            messenger,
        )
    )
    command_dispatcher = CommandDispatcher(
        catalog,
        services.command_access,
        services.telegram_bot_username,
        flow_runner,
    )
    router.message.register(
        command_dispatcher.dispatch,
        F.text.startswith("/"),
    )
    coffee_callbacks = CoffeeCallbackController(
        services.coffee,
        CoffeeCommandRenderer(services.timezone_name),
        CallbackErrorRenderer(error_renderer),
    )
    poll_answers = PollAnswerController(services.poll_tracking, services.lunch_publisher)
    router.callback_query.register(
        coffee_callbacks.handle,
        F.data.startswith("coffee:"),
    )
    router.poll_answer.register(poll_answers.handle)
    router.message.register(flow_runner.handle_message, ActiveFlowState.active)
    return router
