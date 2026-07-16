from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from office_food_bot.features.polls.options import PollOption


class PollKind(StrEnum):
    LUNCH_ATTENDANCE_V1 = "lunch_attendance_v1"
    LUNCH_PLACE_SKYLINE_V1 = "lunch_place_skyline_v1"
    LUNCH_PLACE_ROSE_V1 = "lunch_place_rose_v1"
    LUNCH_OTHER_FOOD_V1 = "lunch_other_food_v1"


@dataclass(frozen=True)
class StoredPoll:
    poll_id: str
    chat_id: int
    message_id: int
    kind: PollKind
    context_date: date
    published_at: datetime


class PollAction(StrEnum):
    LUNCH_OTHER_FOOD_POLL = "lunch_other_food_poll"


@dataclass(frozen=True, slots=True)
class PollOptionActionDefinition:
    option: PollOption
    action: PollAction


@dataclass(frozen=True, slots=True)
class PollDefinition:
    kind: PollKind
    question: str
    options: tuple[PollOption, ...]
    allows_multiple_answers: bool
    option_actions: tuple[PollOptionActionDefinition, ...] = ()

    def known_options_for_indices(
        self,
        option_indices: tuple[int, ...],
    ) -> frozenset[PollOption]:
        return frozenset(
            self.options[index]
            for index in option_indices
            if 0 <= index < len(self.options)
        )

    def action_for(self, option: PollOption) -> PollAction | None:
        return next(
            (
                definition.action
                for definition in self.option_actions
                if definition.option == option
            ),
            None,
        )


class PollDefinitionCatalog:
    def __init__(self, definitions: tuple[PollDefinition, ...]) -> None:
        self._definitions = {definition.kind: definition for definition in definitions}

    def get(self, kind: PollKind) -> PollDefinition:
        return self._definitions[kind]
