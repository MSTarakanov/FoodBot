from __future__ import annotations

from dataclasses import dataclass

from office_food_bot.services.poll_tracking import PollAction

LUNCH_PLACE_OTHER_OPTION = "не знаю что хочу/хочу что-то другое"


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


SKYLINE_LUNCH_POLLS = OfficeLunchPolls(
    lunch=LunchPollDefinition(
        question="Обед в офисе сегодня",
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
        question="Что едим / заказываем?",
        options=(
            "30 этаж",
            "макдонелдс",
            "домашняя еда",
            LUNCH_PLACE_OTHER_OPTION,
            "посмотреть результаты",
        ),
        allows_multiple_answers=True,
        option_actions=(
            PollOptionActionDefinition(
                option_text=LUNCH_PLACE_OTHER_OPTION,
                action=PollAction.LUNCH_OTHER_FOOD_POLL,
            ),
        ),
    ),
)

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
