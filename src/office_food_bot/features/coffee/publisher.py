from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.enums import ParseMode

from office_food_bot.application.users.models import RegisteredUser
from office_food_bot.features.coffee.callbacks import (
    CoffeeCallbackData,
    CoffeeParticipantAction,
)
from office_food_bot.features.coffee.models import CoffeeSession
from office_food_bot.features.coffee.ports import (
    CoffeeAttendance,
    CoffeeInvitationPreferences,
    CoffeeUserReader,
)
from office_food_bot.features.coffee.rendering import CoffeeCardRenderer
from office_food_bot.features.coffee.user_references import format_user_reference
from office_food_bot.messaging import BotMessenger, InlineChoice


class CoffeeCardPublisher:
    def __init__(
        self,
        users: CoffeeUserReader,
        preferences: CoffeeInvitationPreferences,
        attendance: CoffeeAttendance,
        messenger: BotMessenger,
        renderer: CoffeeCardRenderer,
        timezone_name: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._users = users
        self._preferences = preferences
        self._attendance = attendance
        self._messenger = messenger
        self._renderer = renderer
        self._timezone = ZoneInfo(timezone_name)
        self._clock = clock or (lambda: datetime.now(tz=UTC))

    async def publish_card(
        self,
        bot: Bot,
        session: CoffeeSession,
        participants: Sequence[RegisteredUser],
    ) -> int:
        proposer = self._users.get_by_id(session.last_proposer_user_id)
        if proposer is None:
            raise RuntimeError("Coffee proposer was not found")
        message = await self._messenger.edit_or_send(
            bot,
            session.chat_id,
            session.message_id,
            self._renderer.render(
                session,
                proposer,
                participants,
                self._clock(),
            ),
            reply_markup=self._messenger.inline_keyboard(
                (
                    InlineChoice(
                        "Пойду",
                        CoffeeCallbackData(
                            action=CoffeeParticipantAction.JOIN,
                            session_id=session.id,
                        ).pack(),
                    ),
                    InlineChoice(
                        "Не пойду",
                        CoffeeCallbackData(
                            action=CoffeeParticipantAction.LEAVE,
                            session_id=session.id,
                        ).pack(),
                    ),
                )
            ),
            parse_mode=ParseMode.HTML,
        )
        return message.message_id

    async def mark_card_completed(
        self,
        bot: Bot,
        session: CoffeeSession,
        participants: Sequence[RegisteredUser],
    ) -> None:
        if session.message_id is None:
            return
        proposer = self._users.get_by_id(session.last_proposer_user_id)
        if proposer is None:
            return
        await self._messenger.try_edit_message(
            bot,
            session.chat_id,
            session.message_id,
            self._renderer.render_completed(session, proposer, participants),
            parse_mode=ParseMode.HTML,
        )

    async def send_shout(
        self,
        bot: Bot,
        session: CoffeeSession,
        participants: Sequence[RegisteredUser],
    ) -> None:
        participant_ids = {participant.id for participant in participants}
        today = self._clock().astimezone(self._timezone).date()
        invitees = tuple(
            user
            for user in self._attendance.list_office_users(session.chat_id, today)
            if user.id not in participant_ids
            and self._preferences.for_user(user.id).coffee_enabled
        )
        if not invitees:
            return
        references = " ".join(format_user_reference(user) for user in invitees)
        await self._messenger.try_send(
            bot,
            session.chat_id,
            f"{references}, присоединяйтесь на кофе.",
        )

    async def send_reschedule_notification(
        self,
        bot: Bot,
        proposer: RegisteredUser,
        session: CoffeeSession,
    ) -> None:
        if session.message_id is None:
            return
        local_time = session.scheduled_at.astimezone(self._timezone).strftime("%H:%M")
        await self._messenger.try_send(
            bot,
            session.chat_id,
            f"{proposer.display_name} предлагает новое время кофе: {local_time}.",
            reply_to_message_id=session.message_id,
        )

    async def replace_pin(
        self,
        bot: Bot,
        previous_session: CoffeeSession | None,
        current_session: CoffeeSession,
    ) -> None:
        if current_session.message_id is None:
            return
        previous_message_id = None
        if previous_session is not None:
            previous_message_id = previous_session.message_id
        if previous_message_id == current_session.message_id:
            return
        if previous_message_id is not None:
            await self._messenger.try_unpin_chat_message(
                bot,
                current_session.chat_id,
                previous_message_id,
            )
        await self._messenger.try_pin_chat_message(
            bot,
            current_session.chat_id,
            current_session.message_id,
        )

    async def unpin(self, bot: Bot, session: CoffeeSession) -> None:
        if session.message_id is None:
            return
        await self._messenger.try_unpin_chat_message(
            bot,
            session.chat_id,
            session.message_id,
        )

    async def send_ready_notification(
        self,
        bot: Bot,
        session: CoffeeSession,
        participants: Sequence[RegisteredUser],
    ) -> bool:
        references = " ".join(format_user_reference(user) for user in participants)
        return await self._messenger.try_send(
            bot,
            session.chat_id,
            f"☕ Пора идти за кофе!\n{references}",
        )
