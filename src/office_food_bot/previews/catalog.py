from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from office_food_bot.messaging import MessagePayload

type PreviewBuilder = Callable[[], MessagePayload]


@dataclass(frozen=True, slots=True)
class PreviewDefinition:
    name: str
    build: PreviewBuilder


class MessagePreviewCatalog:
    def __init__(self, definitions: Iterable[PreviewDefinition]) -> None:
        definition_list = tuple(definitions)
        definitions_by_name = {
            definition.name: definition for definition in definition_list
        }
        if not definitions_by_name:
            raise ValueError("At least one message preview must be registered")
        if len(definitions_by_name) != len(definition_list):
            raise ValueError("Message preview names must be unique")
        self._definitions = definitions_by_name

    @property
    def cases(self) -> tuple[str, ...]:
        return tuple(self._definitions)

    def render(self, raw_case: str) -> MessagePayload | None:
        definition = self._definitions.get(raw_case.strip().casefold())
        if definition is None:
            return None
        return definition.build()

    def help_text(self) -> str:
        commands = "\n".join(f"/test {case}" for case in self.cases)
        return f"Доступные тестовые сообщения:\n{commands}"
