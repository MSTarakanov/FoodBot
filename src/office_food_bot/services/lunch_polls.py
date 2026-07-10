from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from office_food_bot.services.poll_tracking import PollAction

LUNCH_PLACE_OTHER_OPTION = "не знаю что хочу/хочу что-то другое"
LUNCH_POLL_QUESTION = "Обед в офисе сегодня"
LUNCH_PLACE_POLL_QUESTION = "Что едим / заказываем?"


class LunchOfficeSelection(StrEnum):
    AUTOMATIC = "automatic"
    SKYLINE = "skyline"
    ROSE = "rose"


@dataclass(frozen=True, slots=True)
class PollOptionActionDefinition:
    option_text: str
    action: PollAction


@dataclass(frozen=True, slots=True)
class LunchPollDefinition:
    question: str
    options: tuple[str, ...]
    allows_multiple_answers: bool
    option_actions: tuple[PollOptionActionDefinition, ...] = ()

    def option_actions_by_index(self) -> dict[int, PollAction]:
        return {
            self.options.index(option_action.option_text): option_action.action
            for option_action in self.option_actions
        }


@dataclass(frozen=True, slots=True)
class OfficeLunchPolls:
    lunch: LunchPollDefinition
    place: LunchPollDefinition


LUNCH_PLACE_OTHER_OPTION_ACTION = PollOptionActionDefinition(
    option_text=LUNCH_PLACE_OTHER_OPTION,
    action=PollAction.LUNCH_OTHER_FOOD_POLL,
)

LUNCH_ATTENDANCE_POLL = LunchPollDefinition(
    question=LUNCH_POLL_QUESTION,
    options=(
        "са собом",
        "кушаю в офисе",
        "заказал бы что-то",
        "сижу дома",
        "поел/поем самостоятельно",
        "не решил еще",
        "ахахахахаххаахаха",
    ),
    allows_multiple_answers=False,
)

SKYLINE_LUNCH_POLLS = OfficeLunchPolls(
    lunch=LUNCH_ATTENDANCE_POLL,
    place=LunchPollDefinition(
        question=LUNCH_PLACE_POLL_QUESTION,
        options=(
            "30 этаж",
            "макдонелдс",
            "домашняя еда",
            LUNCH_PLACE_OTHER_OPTION,
            "посмотреть результаты",
        ),
        allows_multiple_answers=True,
        option_actions=(LUNCH_PLACE_OTHER_OPTION_ACTION,),
    ),
)

ROSE_LUNCH_POLLS = OfficeLunchPolls(
    lunch=LUNCH_ATTENDANCE_POLL,
    place=LunchPollDefinition(
        question=LUNCH_PLACE_POLL_QUESTION,
        options=(
            "березка",
            "салатница",
            "сходил бы куда-то поесть рядом",
            LUNCH_PLACE_OTHER_OPTION,
            "посмотреть результаты",
        ),
        allows_multiple_answers=True,
        option_actions=(LUNCH_PLACE_OTHER_OPTION_ACTION,),
    ),
)

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

LUNCH_OTHER_FOOD_POLL = LunchPollDefinition(
    question="Закажем ...",
    options=(
        "другой бургер",
        "шаурма",
        "поке",
        "пицца",
    ),
    allows_multiple_answers=True,
)
