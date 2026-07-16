from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from office_food_bot.commanding.contracts import CommandContext

SOURCE_ROOT = Path(__file__).parents[1] / "src" / "office_food_bot"
COMMAND_ROOT = SOURCE_ROOT / "commands"
CONTROLLER_ROOT = SOURCE_ROOT / "controllers"
COMMAND_SUPPORT_MODULES = frozenset({
    "__init__.py",
    "factory.py",
    "presence.py",
    "router.py",
})
TRANSITIONAL_SYMBOLS = (
    "RawArguments",
    "RawArgumentsParser",
    "CommandObject",
    "CommandArgumentPattern",
    "CommandScopeOverride",
    "scope_overrides",
)


def test_command_context_contains_only_update_runtime_data() -> None:
    assert tuple(field.name for field in fields(CommandContext)) == (
        "message",
        "bot",
        "state",
        "profile",
        "invocation",
    )


def test_transitional_command_api_is_absent_from_source_tree() -> None:
    source = "\n".join(path.read_text() for path in SOURCE_ROOT.rglob("*.py"))

    assert all(symbol not in source for symbol in TRANSITIONAL_SYMBOLS)


def test_concrete_command_modules_define_one_command_class() -> None:
    for path in COMMAND_ROOT.glob("*.py"):
        if path.name in COMMAND_SUPPORT_MODULES:
            continue
        command_classes = tuple(
            node.name
            for node in ast.parse(path.read_text()).body
            if isinstance(node, ast.ClassDef) and node.name.endswith("Command")
        )
        assert len(command_classes) == 1, f"{path.name}: {command_classes}"


def test_commands_have_no_top_level_async_handlers() -> None:
    for path in COMMAND_ROOT.glob("*.py"):
        top_level_async_functions = tuple(
            node.name
            for node in ast.parse(path.read_text()).body
            if isinstance(node, ast.AsyncFunctionDef)
        )
        assert top_level_async_functions == (), (
            f"{path.name}: {top_level_async_functions}"
        )


def test_commands_and_controllers_do_not_receive_service_container() -> None:
    for root in (COMMAND_ROOT, CONTROLLER_ROOT):
        for path in root.glob("*.py"):
            if path.name in {"factory.py", "router.py"}:
                continue
            assert "BotServices" not in path.read_text(), path.name


def test_commands_and_controllers_do_not_manage_dispatch_lifecycle() -> None:
    for root in (COMMAND_ROOT, CONTROLLER_ROOT):
        for path in root.glob("*.py"):
            source = path.read_text()
            assert ".state.clear(" not in source, path.name
            assert "telegram_profile_from_message" not in source, path.name
            assert "context.messenger" not in source, path.name
            assert "context.catalog" not in source, path.name
