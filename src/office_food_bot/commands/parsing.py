from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedCommand:
    name: str
    arguments: str | None
    target_bot_username: str | None


def parse_command(text: str | None) -> ParsedCommand | None:
    if text is None or not text.startswith("/"):
        return None

    text_parts = text.split(maxsplit=1)
    command_reference = text_parts[0].removeprefix("/")
    if not command_reference:
        return None

    command_parts = command_reference.split("@", maxsplit=1)
    command_name = command_parts[0].casefold()
    if not command_name:
        return None

    arguments = None
    if len(text_parts) == 2:
        arguments = text_parts[1]

    target_bot_username = None
    if len(command_parts) == 2:
        target_bot_username = command_parts[1]

    return ParsedCommand(command_name, arguments, target_bot_username)


def is_for_another_bot(parsed_command: ParsedCommand, bot_username: str) -> bool:
    if parsed_command.target_bot_username is None:
        return False
    return parsed_command.target_bot_username.casefold() != bot_username.casefold()
