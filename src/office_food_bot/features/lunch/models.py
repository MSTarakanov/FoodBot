from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class LunchAutoChat:
    chat_id: int
    title: str | None
    enabled: bool


@dataclass(frozen=True)
class LunchPinnedMessage:
    chat_id: int
    message_id: int
    lunch_date: date
