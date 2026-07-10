from datetime import date

import pytest

from office_food_bot.services.lunch_polls import (
    LUNCH_PLACE_OTHER_OPTION,
    ROSE_LUNCH_POLLS,
    SKYLINE_LUNCH_POLLS,
    LunchOfficeSelection,
    LunchPollCatalog,
    parse_lunch_office_selection,
)
from office_food_bot.services.poll_tracking import PollAction


def test_skyline_place_poll_maps_other_option_to_follow_up_action() -> None:
    other_option_index = SKYLINE_LUNCH_POLLS.place.options.index(
        LUNCH_PLACE_OTHER_OPTION
    )

    assert SKYLINE_LUNCH_POLLS.place.option_actions_by_index() == {
        other_option_index: PollAction.LUNCH_OTHER_FOOD_POLL,
    }


def test_lunch_poll_catalog_uses_skyline_outside_tuesday() -> None:
    catalog = LunchPollCatalog()

    assert (
        catalog.select(LunchOfficeSelection.AUTOMATIC, date(2026, 7, 6))
        is SKYLINE_LUNCH_POLLS
    )
    assert (
        catalog.select(LunchOfficeSelection.AUTOMATIC, date(2026, 7, 8))
        is SKYLINE_LUNCH_POLLS
    )
    assert (
        catalog.select(LunchOfficeSelection.AUTOMATIC, date(2026, 7, 12))
        is SKYLINE_LUNCH_POLLS
    )


def test_lunch_poll_catalog_uses_rose_on_tuesday() -> None:
    catalog = LunchPollCatalog()

    assert (
        catalog.select(LunchOfficeSelection.AUTOMATIC, date(2026, 7, 7))
        is ROSE_LUNCH_POLLS
    )


def test_lunch_poll_catalog_allows_explicit_office_selection() -> None:
    catalog = LunchPollCatalog()

    assert (
        catalog.select(LunchOfficeSelection.ROSE, date(2026, 7, 6))
        is ROSE_LUNCH_POLLS
    )
    assert (
        catalog.select(LunchOfficeSelection.SKYLINE, date(2026, 7, 7))
        is SKYLINE_LUNCH_POLLS
    )


@pytest.mark.parametrize(
    ("raw_argument", "expected_selection"),
    [
        (None, LunchOfficeSelection.AUTOMATIC),
        ("", LunchOfficeSelection.AUTOMATIC),
        ("rose", LunchOfficeSelection.ROSE),
        ("роза", LunchOfficeSelection.ROSE),
        ("skyline", LunchOfficeSelection.SKYLINE),
        ("скайлайн", LunchOfficeSelection.SKYLINE),
        ("  RoSe  ", LunchOfficeSelection.ROSE),
    ],
)
def test_lunch_office_selection_parser_accepts_supported_aliases(
    raw_argument: str | None,
    expected_selection: LunchOfficeSelection,
) -> None:
    assert parse_lunch_office_selection(raw_argument) == expected_selection


def test_lunch_office_selection_parser_rejects_unknown_argument() -> None:
    assert parse_lunch_office_selection("office") is None


def test_rose_poll_definitions_have_office_specific_options() -> None:
    assert ROSE_LUNCH_POLLS.lunch.options == (
        "са собом",
        "кушаю в офисе",
        "заказал бы что-то",
        "сходил бы куда-то поесть",
        "сижу дома",
        "поел/поем самостоятельно",
        "не решил еще",
        "ахахахахаххаахаха",
    )
    assert ROSE_LUNCH_POLLS.place.options == (
        "Березка",
        "Салатница",
        LUNCH_PLACE_OTHER_OPTION,
        "посмотреть результаты",
    )
    other_option_index = ROSE_LUNCH_POLLS.place.options.index(
        LUNCH_PLACE_OTHER_OPTION
    )
    assert ROSE_LUNCH_POLLS.place.option_actions_by_index() == {
        other_option_index: PollAction.LUNCH_OTHER_FOOD_POLL,
    }
