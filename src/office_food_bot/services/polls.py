from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from office_food_bot.models import PollKind
from office_food_bot.poll_options import PollOption


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
