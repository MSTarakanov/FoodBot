from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from office_food_bot.commanding.contracts import CommandContext

SOURCE_ROOT = Path(__file__).parents[1] / "src" / "office_food_bot"
COMMAND_ROOT = SOURCE_ROOT / "commands"
FEATURE_ROOT = SOURCE_ROOT / "features"
LEGACY_HORIZONTAL_PACKAGES = ("controllers", "presenters", "services")
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
    "ErrorRenderContext",
    "UserFacingError",
    "ErrorRendererRegistration",
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
    for path in _command_and_controller_paths():
        if path.name in {"factory.py", "router.py"}:
            continue
        assert "BotDependencies" not in path.read_text(), path.name


def test_commands_and_controllers_do_not_manage_dispatch_lifecycle() -> None:
    for path in _command_and_controller_paths():
        source = path.read_text()
        assert ".state.clear(" not in source, path.name
        assert "telegram_profile_from_message" not in source, path.name
        assert "context.messenger" not in source, path.name
        assert "context.catalog" not in source, path.name


def test_error_rendering_has_no_runtime_type_dispatch_or_registry() -> None:
    error_source = (SOURCE_ROOT / "commanding" / "errors" / "rendering.py").read_text()

    assert "isinstance(" not in error_source
    assert "_renderers" not in error_source


def test_legacy_horizontal_packages_have_no_source_modules() -> None:
    for package_name in LEGACY_HORIZONTAL_PACKAGES:
        package = SOURCE_ROOT / package_name
        assert not tuple(package.rglob("*.py")), package_name


def test_commanding_does_not_depend_on_concrete_features() -> None:
    for path in (SOURCE_ROOT / "commanding").rglob("*.py"):
        assert "office_food_bot.features" not in path.read_text(), path.name


def test_feature_rendering_does_not_load_behavior_or_persistence() -> None:
    forbidden_imports = (".service", ".use_case", ".repository", "office_food_bot.bootstrap")
    for path in FEATURE_ROOT.rglob("rendering.py"):
        source = path.read_text()
        assert all(module not in source for module in forbidden_imports), path


def test_common_error_modules_do_not_own_feature_errors() -> None:
    source = "\n".join(
        path.read_text() for path in (SOURCE_ROOT / "commanding" / "errors").glob("*.py")
    )

    assert "BalanceError" not in source
    assert "CoffeeError" not in source
    assert "RegistrationError" not in source


def test_command_menu_does_not_own_concrete_commands() -> None:
    source = (SOURCE_ROOT / "commanding" / "menu.py").read_text()

    assert "office_food_bot.commands" not in source
    assert "ApproveCommand" not in source


def _command_and_controller_paths() -> tuple[Path, ...]:
    return (
        *COMMAND_ROOT.glob("*.py"),
        *FEATURE_ROOT.rglob("*controller.py"),
    )
