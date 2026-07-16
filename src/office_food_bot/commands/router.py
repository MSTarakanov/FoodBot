from __future__ import annotations

from aiogram import F, Router

from office_food_bot.commanding.catalog import CommandCatalog
from office_food_bot.commanding.dispatcher import CommandDispatcher
from office_food_bot.commanding.errors.models import CommonErrorCode
from office_food_bot.commanding.errors.rendering import (
    CallbackCommonErrorRenderer,
    CoffeeErrorRenderer,
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
    common_error_renderer: ErrorRenderer[CommonErrorCode],
    flow_runner: FlowRunner,
) -> Router:
    messenger = services.messenger
    router = Router(name="commands")
    command_dispatcher = CommandDispatcher(
        catalog,
        services.command_access,
        services.telegram_bot_username,
        flow_runner,
        messenger,
        common_error_renderer,
    )
    router.message.register(
        command_dispatcher.dispatch,
        F.text.startswith("/"),
    )
    coffee_callbacks = CoffeeCallbackController(
        services.coffee,
        services.active_users,
        CoffeeCommandRenderer(services.timezone_name),
        CallbackCommonErrorRenderer(common_error_renderer),
        CoffeeErrorRenderer(),
    )
    poll_answers = PollAnswerController(services.poll_tracking, services.lunch_publisher)
    router.callback_query.register(
        coffee_callbacks.handle,
        F.data.startswith("coffee:"),
    )
    router.poll_answer.register(poll_answers.handle)
    router.message.register(flow_runner.handle_message, ActiveFlowState.active)
    return router
