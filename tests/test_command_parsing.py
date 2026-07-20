import pytest

from office_food_bot.commanding.invocation import (
    ParsedCommand,
    is_for_another_bot,
    parse_command,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("/кофе", ParsedCommand("кофе", None, None)),
        ("/КоФе 15", ParsedCommand("кофе", "15", None)),
        (
            "/кофе@foodbot_dev 16:30",
            ParsedCommand("кофе", "16:30", "foodbot_dev"),
        ),
    ],
)
def test_parse_command_supports_casefold_arguments_and_bot_target(
    text: str,
    expected: ParsedCommand,
) -> None:
    assert parse_command(text) == expected


@pytest.mark.parametrize("text", [None, "", "coffee 15", "/"])
def test_parse_command_ignores_non_commands(text: str | None) -> None:
    assert parse_command(text) is None


def test_command_targeting_compares_bot_username_case_insensitively() -> None:
    current_bot = ParsedCommand("кофе", None, "FoodBot_Dev")
    another_bot = ParsedCommand("кофе", None, "another_bot")

    assert is_for_another_bot(current_bot, "foodbot_dev") is False
    assert is_for_another_bot(another_bot, "foodbot_dev") is True
