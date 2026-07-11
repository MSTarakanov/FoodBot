from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from office_food_bot.models import PollKind, PollOptionKey


class PollAction(StrEnum):
    LUNCH_OTHER_FOOD_POLL = "lunch_other_food_poll"


@dataclass(frozen=True, slots=True)
class PollOptionDefinition:
    key: PollOptionKey
    text: str


@dataclass(frozen=True, slots=True)
class PollOptionActionDefinition:
    option_key: PollOptionKey
    action: PollAction


@dataclass(frozen=True, slots=True)
class PollDefinition:
    kind: PollKind
    question: str
    options: tuple[PollOptionDefinition, ...]
    allows_multiple_answers: bool
    option_actions: tuple[PollOptionActionDefinition, ...] = ()

    def option_texts(self) -> tuple[str, ...]:
        return tuple(option.text for option in self.options)

    def known_keys_for_indices(
        self,
        option_indices: tuple[int, ...],
    ) -> frozenset[PollOptionKey]:
        return frozenset(
            self.options[index].key
            for index in option_indices
            if 0 <= index < len(self.options)
        )

    def action_for(self, option_key: PollOptionKey) -> PollAction | None:
        return next(
            (
                definition.action
                for definition in self.option_actions
                if definition.option_key == option_key
            ),
            None,
        )


class PollDefinitionCatalog:
    def __init__(self, definitions: tuple[PollDefinition, ...]) -> None:
        self._definitions = {definition.kind: definition for definition in definitions}

    def get(self, kind: PollKind) -> PollDefinition:
        return self._definitions[kind]
