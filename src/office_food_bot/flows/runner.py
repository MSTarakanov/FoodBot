from __future__ import annotations

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from office_food_bot.commanding.contracts import CommandContext
from office_food_bot.commanding.profile import telegram_profile_from_message
from office_food_bot.flows.catalog import FlowCatalog
from office_food_bot.flows.contracts import (
    ChoiceFlowView,
    ClosingFlowView,
    CompleteFlow,
    FlowContext,
    FlowId,
    FlowSession,
    FlowTransition,
    FlowView,
    MoveToStep,
    StartableFlow,
    StayOnStep,
    TextFlowView,
)
from office_food_bot.messaging import BotMessenger

FLOW_SESSION_KEY = "flow_session"


class ActiveFlowState(StatesGroup):
    active = State()


class FlowRunner:
    def __init__(self, catalog: FlowCatalog, messenger: BotMessenger) -> None:
        self._catalog = catalog
        self._messenger = messenger

    async def start[RequestT](
        self,
        flow: StartableFlow[RequestT],
        command_context: CommandContext,
        request: RequestT,
    ) -> None:
        await command_context.state.clear()
        context = self._from_command_context(command_context)
        transition = await flow.start(context, request)
        await self._apply(context, flow.flow_id, transition)

    async def handle_message(
        self,
        message: Message,
        bot: Bot,
        state: FSMContext,
    ) -> None:
        context = self._from_message(message, bot, state)
        session = await self._require_session(state)
        flow = self._catalog.resolve(session.flow_id)
        if flow is None:
            await state.clear()
            raise RuntimeError(f"Unknown active flow: {session.flow_id.value}")
        transition = await flow.handle(context, session)
        await self._apply(context, flow.flow_id, transition)

    async def cancel(self, command_context: CommandContext) -> None:
        state = command_context.state
        session = await self._session(state)
        if session is None:
            if await state.get_state() is None:
                await self._messenger.reply(
                    command_context.message,
                    "Нет активного сценария.",
                )
                return
            await state.clear()
            await self._messenger.reply(
                command_context.message,
                "Текущий сценарий отменен.",
                reply_markup=self._messenger.remove_keyboard(),
            )
            return

        flow = self._catalog.resolve(session.flow_id)
        if flow is None:
            await state.clear()
            raise RuntimeError(f"Unknown active flow: {session.flow_id.value}")
        context = self._from_command_context(command_context)
        transition = await flow.cancel(context, session)
        if not isinstance(transition, CompleteFlow):
            raise RuntimeError(
                f"Flow {flow.flow_id.value} did not complete during cancellation"
            )
        await self._apply(context, flow.flow_id, transition)

    async def abort(
        self,
        message: Message,
        bot: Bot,
        state: FSMContext,
    ) -> None:
        session = await self._session(state)
        if session is not None:
            flow = self._catalog.resolve(session.flow_id)
            if flow is not None:
                await flow.abort(self._from_message(message, bot, state), session)
        await state.clear()

    async def _apply(
        self,
        context: FlowContext,
        flow_id: FlowId,
        transition: FlowTransition,
    ) -> None:
        if isinstance(transition, StayOnStep):
            await self._publish(context, transition.view)
            return
        if isinstance(transition, MoveToStep):
            await context.state.set_state(ActiveFlowState.active)
            await context.state.set_data(
                {
                    FLOW_SESSION_KEY: FlowSession(
                        flow_id=flow_id,
                        step_id=transition.step_id,
                        draft=transition.draft,
                    )
                }
            )
            await self._publish(context, transition.view)
            return
        if isinstance(transition, CompleteFlow):
            await context.state.clear()
            if transition.view is not None:
                await self._publish(context, transition.view)
            if transition.post_action is not None:
                await transition.post_action.execute(context)
            return
        raise RuntimeError(f"Unsupported flow transition: {type(transition).__name__}")

    async def _publish(self, context: FlowContext, view: FlowView) -> None:
        if isinstance(view, TextFlowView):
            await self._messenger.reply(context.message, view.text)
            return
        if isinstance(view, ChoiceFlowView):
            await self._messenger.reply_with_choices(
                context.message,
                view.text,
                view.choices,
                columns=view.columns,
                one_time_keyboard=view.one_time_keyboard,
            )
            return
        if isinstance(view, ClosingFlowView):
            await self._messenger.reply(
                context.message,
                view.text,
                reply_markup=self._messenger.remove_keyboard(),
            )
            return
        raise RuntimeError(f"Unsupported flow view: {type(view).__name__}")

    async def _require_session(self, state: FSMContext) -> FlowSession:
        session = await self._session(state)
        if session is not None:
            return session
        await state.clear()
        raise RuntimeError("Active flow state has no flow session")

    async def _session(self, state: FSMContext) -> FlowSession | None:
        data = await state.get_data()
        session = data.get(FLOW_SESSION_KEY)
        if isinstance(session, FlowSession):
            return session
        return None

    def _from_command_context(self, context: CommandContext) -> FlowContext:
        return FlowContext(
            message=context.message,
            bot=context.bot,
            messenger=self._messenger,
            state=context.state,
            profile=context.profile,
        )

    def _from_message(
        self,
        message: Message,
        bot: Bot,
        state: FSMContext,
    ) -> FlowContext:
        return FlowContext(
            message=message,
            bot=bot,
            messenger=self._messenger,
            state=state,
            profile=telegram_profile_from_message(message),
        )
