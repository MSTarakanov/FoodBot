from __future__ import annotations

import pytest

from office_food_bot.boolean_input import parse_confirmation, parse_toggle


@pytest.mark.parametrize("value", ["on", "TRUE", " вкл "])
def test_toggle_enabled_words(value: str) -> None:
    assert parse_toggle(value) is True


@pytest.mark.parametrize("value", ["off", "FALSE", " выкл "])
def test_toggle_disabled_words(value: str) -> None:
    assert parse_toggle(value) is False


@pytest.mark.parametrize("value", ["да", "YES", " y "])
def test_confirmation_accepted_words(value: str) -> None:
    assert parse_confirmation(value) is True


@pytest.mark.parametrize("value", ["нет", "NO", " n "])
def test_confirmation_rejected_words(value: str) -> None:
    assert parse_confirmation(value) is False


@pytest.mark.parametrize("value", ["да", "нет", "yes", "no", "y", "n"])
def test_confirmation_words_are_not_setting_toggles(value: str) -> None:
    assert parse_toggle(value) is None


@pytest.mark.parametrize("value", ["on", "off", "true", "false", "вкл", "выкл"])
def test_toggle_words_are_not_confirmations(value: str) -> None:
    assert parse_confirmation(value) is None


def test_numeric_toggle_is_opt_in() -> None:
    assert parse_toggle("1") is None
    assert parse_toggle("0") is None
    assert parse_toggle("1", allow_numeric=True) is True
    assert parse_toggle("0", allow_numeric=True) is False
