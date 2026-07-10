from datetime import date

from office_food_bot.services.lunch_polls import (
    LUNCH_PLACE_OTHER_OPTION,
    ROSE_LUNCH_POLLS,
    SKYLINE_LUNCH_POLLS,
    LunchPollCatalog,
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

    assert catalog.for_date(date(2026, 7, 6)) is SKYLINE_LUNCH_POLLS
    assert catalog.for_date(date(2026, 7, 8)) is SKYLINE_LUNCH_POLLS
    assert catalog.for_date(date(2026, 7, 12)) is SKYLINE_LUNCH_POLLS


def test_lunch_poll_catalog_uses_rose_on_tuesday() -> None:
    catalog = LunchPollCatalog()

    assert catalog.for_date(date(2026, 7, 7)) is ROSE_LUNCH_POLLS


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
