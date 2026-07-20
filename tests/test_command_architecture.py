from __future__ import annotations

import ast
from collections.abc import Iterable
from dataclasses import dataclass, fields
from importlib.util import resolve_name
from pathlib import Path

from office_food_bot.commanding.contracts import CommandContext

SOURCE_ROOT = Path(__file__).parents[1] / "src" / "office_food_bot"
APPLICATION_ROOT = SOURCE_ROOT / "application"
COMMAND_ROOT = SOURCE_ROOT / "commands"
FEATURE_ROOT = SOURCE_ROOT / "features"
LEGACY_HORIZONTAL_PACKAGES = ("controllers", "presenters", "services")
COMMAND_SUPPORT_MODULES = frozenset({
    "__init__.py",
    "factory.py",
    "presence.py",
    "router.py",
})
TRANSITIONAL_SYMBOLS = frozenset({
    "RawArguments",
    "RawArgumentsParser",
    "CommandObject",
    "CommandArgumentPattern",
    "CommandScopeOverride",
    "ErrorRenderContext",
    "UserFacingError",
    "ErrorRendererRegistration",
    "scope_overrides",
})


@dataclass(frozen=True, slots=True)
class ParsedModule:
    path: Path
    name: str
    tree: ast.Module


def test_command_context_contains_only_update_runtime_data() -> None:
    assert tuple(field.name for field in fields(CommandContext)) == (
        "message",
        "bot",
        "state",
        "profile",
        "invocation",
    )


def test_transitional_command_api_is_absent_from_source_tree() -> None:
    occurrences = {
        symbol: module.path
        for module in _modules_under(SOURCE_ROOT)
        for symbol in _identifiers(module.tree)
        if symbol in TRANSITIONAL_SYMBOLS
    }

    assert occurrences == {}


def test_concrete_command_modules_define_one_command_class() -> None:
    for module in _modules_under(COMMAND_ROOT, recursive=False):
        if module.path.name in COMMAND_SUPPORT_MODULES:
            continue
        command_classes = tuple(
            node.name
            for node in module.tree.body
            if isinstance(node, ast.ClassDef) and node.name.endswith("Command")
        )
        assert len(command_classes) == 1, (
            f"{module.path.name}: {command_classes}"
        )


def test_commands_have_no_top_level_async_handlers() -> None:
    for module in _modules_under(COMMAND_ROOT, recursive=False):
        top_level_async_functions = tuple(
            node.name
            for node in module.tree.body
            if isinstance(node, ast.AsyncFunctionDef)
        )
        assert top_level_async_functions == (), (
            f"{module.path.name}: {top_level_async_functions}"
        )


def test_commands_and_controllers_do_not_receive_service_container() -> None:
    for module in _command_and_controller_modules():
        if module.path.name in {"factory.py", "router.py"}:
            continue
        assert "BotDependencies" not in _identifiers(module.tree), module.path


def test_commands_and_controllers_do_not_manage_dispatch_lifecycle() -> None:
    for module in _command_and_controller_modules():
        identifiers = _identifiers(module.tree)
        assert "telegram_profile_from_message" not in identifiers, module.path
        for node in ast.walk(module.tree):
            match node:
                case ast.Call(
                    func=ast.Attribute(
                        value=ast.Attribute(attr="state"),
                        attr="clear",
                    )
                ):
                    raise AssertionError(f"{module.path}: command clears FSM state")
                case ast.Attribute(
                    value=ast.Name(id="context"),
                    attr="messenger" | "catalog" as attribute,
                ):
                    raise AssertionError(
                        f"{module.path}: command reads context.{attribute}"
                    )


def test_error_rendering_has_no_runtime_type_dispatch_or_registry() -> None:
    module = _parse_module(SOURCE_ROOT / "commanding" / "errors" / "rendering.py")

    assert "isinstance" not in _called_names(module.tree)
    assert "_renderers" not in _identifiers(module.tree)


def test_legacy_horizontal_packages_have_no_source_modules() -> None:
    for package_name in LEGACY_HORIZONTAL_PACKAGES:
        package = SOURCE_ROOT / package_name
        assert not tuple(package.rglob("*.py")), package_name


def test_root_model_and_repository_warehouses_are_absent() -> None:
    assert not (SOURCE_ROOT / "models.py").exists()
    assert not (SOURCE_ROOT / "repositories.py").exists()


def test_database_package_contains_only_schema_and_connection_infrastructure() -> None:
    query_modules = tuple((SOURCE_ROOT / "database").glob("*_queries.py"))

    assert query_modules == ()


def test_commanding_does_not_depend_on_concrete_features() -> None:
    _assert_no_imports(
        _modules_under(SOURCE_ROOT / "commanding"),
        ("office_food_bot.features",),
    )


def test_application_does_not_depend_on_transport_or_features() -> None:
    _assert_no_imports(
        _modules_under(APPLICATION_ROOT),
        (
            "aiogram",
            "office_food_bot.bootstrap",
            "office_food_bot.commanding",
            "office_food_bot.features",
            "office_food_bot.infrastructure",
            "office_food_bot.integrations",
        ),
    )


def test_feature_behavior_depends_on_ports_not_concrete_repositories() -> None:
    adapter_names = {"repository.py", "queries.py", "auto_queries.py", "pin_queries.py"}
    behavior_modules = tuple(
        module
        for module in _modules_under(FEATURE_ROOT)
        if module.path.name not in adapter_names
        and not module.path.name.endswith("_queries.py")
    )

    _assert_no_imports(
        behavior_modules,
        (
            "office_food_bot.infrastructure.persistence",
            ".repository",
        ),
        suffix_match=True,
    )


def test_features_have_no_cyclic_dependencies() -> None:
    graph = _feature_dependency_graph()
    cycle = _find_cycle(graph)

    assert cycle is None, _format_cycle(cycle)


def test_shared_user_access_is_not_a_placeholder_feature() -> None:
    assert not tuple((FEATURE_ROOT / "users").rglob("*.py"))


def test_feature_rendering_does_not_load_behavior_or_persistence() -> None:
    _assert_no_imports(
        (
            module
            for module in _modules_under(FEATURE_ROOT)
            if module.path.name == "rendering.py"
        ),
        (
            ".service",
            ".use_case",
            ".repository",
            "office_food_bot.bootstrap",
        ),
        suffix_match=True,
    )


def test_common_error_modules_do_not_own_feature_errors() -> None:
    feature_error_prefixes = ("BalanceError", "CoffeeError", "RegistrationError")
    occurrences = {
        identifier: module.path
        for module in _modules_under(SOURCE_ROOT / "commanding" / "errors")
        for identifier in _identifiers(module.tree)
        if identifier.startswith(feature_error_prefixes)
    }

    assert occurrences == {}


def test_command_menu_does_not_own_concrete_commands() -> None:
    module = _parse_module(SOURCE_ROOT / "commanding" / "menu.py")

    assert not _matching_imports(module, ("office_food_bot.commands",))
    assert "ApproveCommand" not in _identifiers(module.tree)


def _modules_under(root: Path, *, recursive: bool = True) -> tuple[ParsedModule, ...]:
    paths = root.rglob("*.py") if recursive else root.glob("*.py")
    return tuple(_parse_module(path) for path in sorted(paths))


def _parse_module(path: Path) -> ParsedModule:
    return ParsedModule(path, _module_name(path), ast.parse(path.read_text()))


def _module_name(path: Path) -> str:
    relative = path.relative_to(SOURCE_ROOT.parent).with_suffix("")
    parts = relative.parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _identifiers(tree: ast.AST) -> frozenset[str]:
    identifiers: set[str] = set()
    for node in ast.walk(tree):
        match node:
            case ast.Name(id=name) | ast.ClassDef(name=name) | ast.FunctionDef(name=name):
                identifiers.add(name)
            case ast.AsyncFunctionDef(name=name) | ast.Attribute(attr=name):
                identifiers.add(name)
            case ast.arg(arg=name):
                identifiers.add(name)
            case ast.keyword(arg=name) if name is not None:
                identifiers.add(name)
    return frozenset(identifiers)


def _called_names(tree: ast.AST) -> frozenset[str]:
    return frozenset(
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    )


def _imports(module: ParsedModule) -> frozenset[str]:
    imported: set[str] = set()
    package = module.name if module.path.name == "__init__.py" else module.name.rpartition(".")[0]
    for node in ast.walk(module.tree):
        match node:
            case ast.Import(names=names):
                imported.update(alias.name for alias in names)
            case ast.ImportFrom(module=imported_module, level=level, names=names):
                if level:
                    relative_name = "." * level + (imported_module or "")
                    base = resolve_name(relative_name, package)
                else:
                    base = imported_module or ""
                if base:
                    imported.add(base)
                if imported_module is None:
                    imported.update(f"{base}.{alias.name}" for alias in names)
    return frozenset(imported)


def _assert_no_imports(
    modules: Iterable[ParsedModule],
    forbidden: tuple[str, ...],
    *,
    suffix_match: bool = False,
) -> None:
    for module in modules:
        matches = _matching_imports(module, forbidden, suffix_match=suffix_match)
        assert matches == (), f"{module.path}: {matches}"


def _matching_imports(
    module: ParsedModule,
    forbidden: tuple[str, ...],
    *,
    suffix_match: bool = False,
) -> tuple[str, ...]:
    return tuple(
        imported
        for imported in sorted(_imports(module))
        if any(
            imported == prefix
            or imported.startswith(f"{prefix}.")
            or (suffix_match and prefix in imported)
            for prefix in forbidden
        )
    )


def _feature_dependency_graph() -> dict[str, frozenset[str]]:
    feature_names = frozenset(
        path.name
        for path in FEATURE_ROOT.iterdir()
        if path.is_dir() and tuple(path.rglob("*.py"))
    )
    graph: dict[str, frozenset[str]] = {}
    for feature_name in feature_names:
        dependencies: set[str] = set()
        for module in _modules_under(FEATURE_ROOT / feature_name):
            for imported in _imports(module):
                parts = imported.split(".")
                if len(parts) < 3 or parts[:2] != ["office_food_bot", "features"]:
                    continue
                target = parts[2]
                if target in feature_names and target != feature_name:
                    dependencies.add(target)
        graph[feature_name] = frozenset(dependencies)
    return graph


def _find_cycle(graph: dict[str, frozenset[str]]) -> tuple[str, ...] | None:
    visited: set[str] = set()
    active: list[str] = []

    def visit(node: str) -> tuple[str, ...] | None:
        if node in active:
            cycle_start = active.index(node)
            return (*active[cycle_start:], node)
        if node in visited:
            return None
        active.append(node)
        for dependency in sorted(graph[node]):
            cycle = visit(dependency)
            if cycle is not None:
                return cycle
        active.pop()
        visited.add(node)
        return None

    for node in sorted(graph):
        cycle = visit(node)
        if cycle is not None:
            return cycle
    return None


def _format_cycle(cycle: tuple[str, ...] | None) -> str:
    if cycle is None:
        return ""
    return "Feature dependency cycle: " + " -> ".join(cycle)


def _command_and_controller_modules() -> tuple[ParsedModule, ...]:
    return (
        *_modules_under(COMMAND_ROOT, recursive=False),
        *(
            _parse_module(path)
            for path in sorted(FEATURE_ROOT.rglob("*controller.py"))
        ),
    )
