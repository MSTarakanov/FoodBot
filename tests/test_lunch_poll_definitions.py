from office_food_bot.services.lunch_polls import (
    LUNCH_PLACE_OTHER_OPTION,
    SKYLINE_LUNCH_POLLS,
)
from office_food_bot.services.poll_tracking import PollAction


def test_skyline_place_poll_maps_other_option_to_follow_up_action() -> None:
    other_option_index = SKYLINE_LUNCH_POLLS.place.options.index(
        LUNCH_PLACE_OTHER_OPTION
    )

    assert SKYLINE_LUNCH_POLLS.place.option_actions_by_index() == {
        other_option_index: PollAction.LUNCH_OTHER_FOOD_POLL,
    }
