from __future__ import annotations

TOGGLE_ENABLED_WORDS = frozenset({"on", "true", "вкл"})
TOGGLE_DISABLED_WORDS = frozenset({"off", "false", "выкл"})
CONFIRMATION_ACCEPTED_WORDS = frozenset({"да", "yes", "y"})
CONFIRMATION_REJECTED_WORDS = frozenset({"нет", "no", "n"})

_NUMERIC_ENABLED_WORDS = frozenset({"1"})
_NUMERIC_DISABLED_WORDS = frozenset({"0"})


def parse_toggle(raw_value: str, *, allow_numeric: bool = False) -> bool | None:
    value = _normalized(raw_value)
    if value in TOGGLE_ENABLED_WORDS or (
        allow_numeric and value in _NUMERIC_ENABLED_WORDS
    ):
        return True
    if value in TOGGLE_DISABLED_WORDS or (
        allow_numeric and value in _NUMERIC_DISABLED_WORDS
    ):
        return False
    return None


def parse_confirmation(raw_value: str) -> bool | None:
    value = _normalized(raw_value)
    if value in CONFIRMATION_ACCEPTED_WORDS:
        return True
    if value in CONFIRMATION_REJECTED_WORDS:
        return False
    return None


def _normalized(value: str) -> str:
    return value.strip().casefold()
