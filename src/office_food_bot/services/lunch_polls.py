from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from office_food_bot.services.poll_tracking import PollAction

LUNCH_PLACE_OTHER_OPTION = "не знаю что хочу/хочу что-то другое"
LUNCH_POLL_QUESTION = "Обед в офисе сегодня"
LUNCH_PLACE_POLL_QUESTION = "Что едим / заказываем?"


class OfficeLocation(StrEnum):
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

SKYLINE_LUNCH_POLLS = OfficeLunchPolls(
    lunch=LunchPollDefinition(
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
    ),
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
    lunch=LunchPollDefinition(
        question=LUNCH_POLL_QUESTION,
        options=(
            "са собом",
            "кушаю в офисе",
            "заказал бы что-то",
            "сходил бы куда-то поесть",
            "сижу дома",
            "поел/поем самостоятельно",
            "не решил еще",
            "ахахахахаххаахаха",
        ),
        allows_multiple_answers=False,
    ),
    place=LunchPollDefinition(
        question=LUNCH_PLACE_POLL_QUESTION,
        options=(
            "Березка",
            "Салатница",
            LUNCH_PLACE_OTHER_OPTION,
            "посмотреть результаты",
        ),
        allows_multiple_answers=True,
        option_actions=(LUNCH_PLACE_OTHER_OPTION_ACTION,),
    ),
)

_OFFICE_LUNCH_POLLS = {
    OfficeLocation.SKYLINE: SKYLINE_LUNCH_POLLS,
    OfficeLocation.ROSE: ROSE_LUNCH_POLLS,
}


class LunchPollCatalog:
    def for_date(self, lunch_date: date) -> OfficeLunchPolls:
        office = OfficeLocation.SKYLINE
        if lunch_date.weekday() == calendar.TUESDAY:
            office = OfficeLocation.ROSE
        return _OFFICE_LUNCH_POLLS[office]

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
