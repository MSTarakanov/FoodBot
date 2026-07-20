from __future__ import annotations

from aiogram import F, Router

from office_food_bot.bootstrap import BotDependencies
from office_food_bot.commanding.catalog import CommandCatalog
from office_food_bot.commanding.dispatcher import CommandDispatcher
from office_food_bot.commanding.errors.models import CommonErrorCode
from office_food_bot.commanding.errors.rendering import (
    CallbackCommonErrorRenderer,
    ErrorRenderer,
)
from office_food_bot.features.coffee.callback_controller import (
    CoffeeCardCallbackController,
)
from office_food_bot.features.coffee.errors import CoffeeErrorRenderer
from office_food_bot.features.coffee.rendering import CoffeeCommandRenderer
from office_food_bot.features.lunch.poll_controller import PollAnswerController
from office_food_bot.flows.runner import ActiveFlowState, FlowRunner


def create_command_router(
    dependencies: BotDependencies,
    catalog: CommandCatalog,
    common_error_renderer: ErrorRenderer[CommonErrorCode],
    flow_runner: FlowRunner,
) -> Router:
    messenger = dependencies.messenger
    router = Router(name="commands")
    command_dispatcher = CommandDispatcher(
        catalog,
        dependencies.command_access,
        dependencies.telegram_bot_username,
        flow_runner,
        messenger,
        common_error_renderer,
    )
    router.message.register(
        command_dispatcher.dispatch,
        F.text.startswith("/"),
    )
    coffee_callbacks = CoffeeCardCallbackController(
        dependencies.coffee,
        dependencies.active_users,
        CoffeeCommandRenderer(dependencies.timezone_name),
        CallbackCommonErrorRenderer(common_error_renderer),
        CoffeeErrorRenderer(),
    )
    poll_answers = PollAnswerController(dependencies.poll_tracking, dependencies.lunch_publisher)
    router.callback_query.register(
        coffee_callbacks.handle,
        F.data.startswith("coffee:"),
    )
    router.poll_answer.register(poll_answers.handle)
    router.message.register(flow_runner.handle_message, ActiveFlowState.active)
    return router
