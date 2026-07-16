from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CoffeeParticipantAction(StrEnum):
    JOIN = "join"
    LEAVE = "leave"


@dataclass(frozen=True, slots=True)
class CoffeeCallbackData:
    action: CoffeeParticipantAction
    session_id: int

    def pack(self) -> str:
        return f"coffee:{self.action.value}:{self.session_id}"

    @classmethod
    def unpack(cls, value: str) -> CoffeeCallbackData | None:
        prefix, separator, payload = value.partition(":")
        if prefix != "coffee" or not separator:
            return None
        raw_action, separator, raw_session_id = payload.partition(":")
        if not separator or not raw_session_id.isdigit():
            return None
        try:
            action = CoffeeParticipantAction(raw_action)
        except ValueError:
            return None
        return cls(action, int(raw_session_id))
