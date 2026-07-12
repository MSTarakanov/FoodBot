from __future__ import annotations

from datetime import date

from office_food_bot.models import PollKind, RegisteredUser
from office_food_bot.poll_options import PollOption
from office_food_bot.repositories import PollRepository

OFFICE_ATTENDANCE_OPTIONS = frozenset(
    {
        PollOption.LUNCH_BRING_OWN,
        PollOption.LUNCH_EAT_IN_OFFICE,
        PollOption.LUNCH_WOULD_ORDER,
    }
)
LUNCH_ATTENDANCE_KINDS = (PollKind.LUNCH_ATTENDANCE_V1,)


class LunchAttendanceService:
    def __init__(self, polls: PollRepository) -> None:
        self._polls = polls

    def list_office_users(
        self,
        chat_id: int,
        context_date: date,
    ) -> tuple[RegisteredUser, ...]:
        poll = self._polls.latest_for_kinds(
            chat_id,
            context_date,
            LUNCH_ATTENDANCE_KINDS,
        )
        if poll is None:
            return ()
        return self._polls.list_active_users_with_any_option(
            poll.poll_id,
            OFFICE_ATTENDANCE_OPTIONS,
        )
