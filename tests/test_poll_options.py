from office_food_bot.poll_options import PollOption


def test_poll_options_have_unique_stable_values_and_display_values() -> None:
    options = tuple(PollOption)

    assert len(PollOption.__members__) == len(options)
    assert all(option.value for option in options)
    assert all(option.display_value.strip() for option in options)
    assert all(option.value != option.display_value for option in options)


def test_poll_option_round_trips_database_value() -> None:
    option = PollOption.LUNCH_EAT_IN_OFFICE

    assert PollOption.from_value(option.value) is option
