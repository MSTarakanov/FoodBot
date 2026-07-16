from __future__ import annotations

from enum import StrEnum
from typing import assert_never


class CoffeeErrorCode(StrEnum):
    INVALID_CALLBACK = "invalid_callback"
    SESSION_ENDED = "session_ended"


class CoffeeErrorRenderer:
    def render(self, code: CoffeeErrorCode) -> str:
        match code:
            case CoffeeErrorCode.INVALID_CALLBACK:
                return "Не понял действие."
            case CoffeeErrorCode.SESSION_ENDED:
                return "Эта встреча уже завершена."
        assert_never(code)
