from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from office_food_bot.models import PollKind
from office_food_bot.poll_options import PollOption
from office_food_bot.services.polls import (
    PollAction,
    PollDefinition,
    PollDefinitionCatalog,
    PollOptionActionDefinition,
)

LUNCH_POLL_QUESTION = "Обед в офисе сегодня"
LUNCH_PLACE_POLL_QUESTION = "Что едим / заказываем?"


class LunchOfficeSelection(StrEnum):
    AUTOMATIC = "automatic"
    SKYLINE = "skyline"
    ROSE = "rose"


@dataclass(frozen=True, slots=True)
class OfficeLunchPolls:
    lunch: PollDefinition
    place: PollDefinition


LUNCH_ATTENDANCE_POLL = PollDefinition(
    kind=PollKind.LUNCH_ATTENDANCE_V1,
    question=LUNCH_POLL_QUESTION,
    options=(
        PollOption.LUNCH_BRING_OWN,
        PollOption.LUNCH_EAT_IN_OFFICE,
        PollOption.LUNCH_WOULD_ORDER,
        PollOption.LUNCH_STAY_HOME,
        PollOption.LUNCH_EAT_INDEPENDENTLY,
        PollOption.LUNCH_UNDECIDED,
        PollOption.LUNCH_NOT_WORKING,
    ),
    allows_multiple_answers=False,
)

SKYLINE_LUNCH_POLLS = OfficeLunchPolls(
    lunch=LUNCH_ATTENDANCE_POLL,
    place=PollDefinition(
        kind=PollKind.LUNCH_PLACE_SKYLINE_V1,
        question=LUNCH_PLACE_POLL_QUESTION,
        options=(
            PollOption.LUNCH_PLACE_SKYLINE_30_FLOOR,
            PollOption.LUNCH_PLACE_MCDONALDS,
            PollOption.LUNCH_PLACE_HOME_FOOD,
            PollOption.LUNCH_PLACE_OTHER,
            PollOption.LUNCH_PLACE_VIEW_RESULTS,
        ),
        allows_multiple_answers=True,
        option_actions=(
            PollOptionActionDefinition(
                PollOption.LUNCH_PLACE_OTHER,
                PollAction.LUNCH_OTHER_FOOD_POLL,
            ),
        ),
    ),
)

ROSE_LUNCH_POLLS = OfficeLunchPolls(
    lunch=LUNCH_ATTENDANCE_POLL,
    place=PollDefinition(
        kind=PollKind.LUNCH_PLACE_ROSE_V1,
        question=LUNCH_PLACE_POLL_QUESTION,
        options=(
            PollOption.LUNCH_PLACE_ROSE_BEREZKA,
            PollOption.LUNCH_PLACE_ROSE_SALATNITSA,
            PollOption.LUNCH_PLACE_EAT_OUT,
            PollOption.LUNCH_PLACE_OTHER,
            PollOption.LUNCH_PLACE_VIEW_RESULTS,
        ),
        allows_multiple_answers=True,
        option_actions=(
            PollOptionActionDefinition(
                PollOption.LUNCH_PLACE_OTHER,
                PollAction.LUNCH_OTHER_FOOD_POLL,
            ),
        ),
    ),
)

LUNCH_OTHER_FOOD_POLL = PollDefinition(
    kind=PollKind.LUNCH_OTHER_FOOD_V1,
    question="Закажем ...",
    options=(
        PollOption.OTHER_FOOD_BURGER,
        PollOption.OTHER_FOOD_SHAWARMA,
        PollOption.OTHER_FOOD_POKE,
        PollOption.OTHER_FOOD_PIZZA,
    ),
    allows_multiple_answers=True,
)

ALL_LUNCH_POLL_DEFINITIONS = (
    LUNCH_ATTENDANCE_POLL,
    SKYLINE_LUNCH_POLLS.place,
    ROSE_LUNCH_POLLS.place,
    LUNCH_OTHER_FOOD_POLL,
)

LUNCH_POLL_DEFINITION_CATALOG = PollDefinitionCatalog(ALL_LUNCH_POLL_DEFINITIONS)

_OFFICE_LUNCH_POLLS = {
    LunchOfficeSelection.SKYLINE: SKYLINE_LUNCH_POLLS,
    LunchOfficeSelection.ROSE: ROSE_LUNCH_POLLS,
}

_LUNCH_OFFICE_ALIASES = {
    "rose": LunchOfficeSelection.ROSE,
    "роза": LunchOfficeSelection.ROSE,
    "skyline": LunchOfficeSelection.SKYLINE,
    "скайлайн": LunchOfficeSelection.SKYLINE,
}


class LunchPollCatalog:
    def select(
        self,
        selection: LunchOfficeSelection,
        lunch_date: date,
    ) -> OfficeLunchPolls:
        resolved_selection = selection
        if selection == LunchOfficeSelection.AUTOMATIC:
            resolved_selection = self._selection_for_date(lunch_date)
        return _OFFICE_LUNCH_POLLS[resolved_selection]

    def _selection_for_date(self, lunch_date: date) -> LunchOfficeSelection:
        if lunch_date.weekday() == calendar.TUESDAY:
            return LunchOfficeSelection.ROSE
        return LunchOfficeSelection.SKYLINE


def parse_lunch_office_selection(
    raw_argument: str | None,
) -> LunchOfficeSelection | None:
    if raw_argument is None or not raw_argument.strip():
        return LunchOfficeSelection.AUTOMATIC
    return _LUNCH_OFFICE_ALIASES.get(raw_argument.strip().casefold())
