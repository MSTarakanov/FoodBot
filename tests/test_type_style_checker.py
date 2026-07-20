from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

CHECKER_PATH = Path(__file__).parents[1] / "scripts" / "check_type_style.py"
CHECKER_SPEC = importlib.util.spec_from_file_location("check_type_style", CHECKER_PATH)
if CHECKER_SPEC is None or CHECKER_SPEC.loader is None:
    msg = f"Cannot load type style checker from {CHECKER_PATH}"
    raise RuntimeError(msg)

check_type_style = importlib.util.module_from_spec(CHECKER_SPEC)
sys.modules[CHECKER_SPEC.name] = check_type_style
CHECKER_SPEC.loader.exec_module(check_type_style)

Violation = check_type_style.Violation
check_file = check_type_style.check_file


def test_type_style_checker_allows_precise_optional_union(tmp_path: Path) -> None:
    violations = check_source(
        tmp_path,
        "def optional_name(name: str | None) -> str | None:\n"
        "    return name\n",
    )

    assert violations == []


def test_type_style_checker_allows_generic_optional_union(tmp_path: Path) -> None:
    violations = check_source(
        tmp_path,
        "def optional_str[Value](value: Value | None) -> str | None:\n"
        "    if value is None:\n"
        "        return None\n"
        "    return str(value)\n",
    )

    assert violations == []


def test_type_style_checker_rejects_explicit_any(tmp_path: Path) -> None:
    violations = check_source(
        tmp_path,
        "from typing import Any\n"
        "def debug(value: Any) -> None:\n"
        "    return None\n",
    )

    assert violation_codes(violations) == ["TYP001", "TYP001"]


def test_type_style_checker_rejects_non_optional_union(tmp_path: Path) -> None:
    violations = check_source(
        tmp_path,
        "def parse(value: str | int) -> str:\n"
        "    return str(value)\n",
    )

    assert violation_codes(violations) == ["TYP002"]


def test_type_style_checker_rejects_object_annotations(tmp_path: Path) -> None:
    violations = check_source(
        tmp_path,
        "def parse(value: object) -> str:\n"
        "    return str(value)\n",
    )

    assert violation_codes(violations) == ["TYP003"]


def test_type_style_checker_rejects_nested_object_annotations(tmp_path: Path) -> None:
    violations = check_source(
        tmp_path,
        "def parse(values: list[object]) -> list[str]:\n"
        "    return [str(value) for value in values]\n",
    )

    assert violation_codes(violations) == ["TYP003"]


def test_type_style_checker_rejects_isinstance(tmp_path: Path) -> None:
    violations = check_source(
        tmp_path,
        "def parse(value: str) -> str:\n"
        "    if isinstance(value, str):\n"
        "        return value\n"
        "    return ''\n",
    )

    assert violation_codes(violations) == ["TYP004"]


def test_type_style_checker_rejects_aliased_isinstance(tmp_path: Path) -> None:
    violations = check_source(
        tmp_path,
        "from builtins import isinstance as is_instance\n"
        "def parse(value: str) -> str:\n"
        "    if is_instance(value, str):\n"
        "        return value\n"
        "    return ''\n",
    )

    assert violation_codes(violations) == ["TYP004"]


def test_type_style_checker_rejects_builtins_isinstance(tmp_path: Path) -> None:
    violations = check_source(
        tmp_path,
        "import builtins as builtin_types\n"
        "def parse(value: str) -> str:\n"
        "    if builtin_types.isinstance(value, str):\n"
        "        return value\n"
        "    return ''\n",
    )

    assert violation_codes(violations) == ["TYP004"]


def test_type_style_checker_allows_pattern_matching(tmp_path: Path) -> None:
    violations = check_source(
        tmp_path,
        "def parse(value: str) -> str:\n"
        "    match value:\n"
        "        case str():\n"
        "            return value\n"
        "    return ''\n",
    )

    assert violations == []


def check_source(tmp_path: Path, source: str) -> list[Violation]:
    path = tmp_path / "example.py"
    path.write_text(source)
    return check_file(path)


def violation_codes(violations: list[Violation]) -> list[str]:
    return [violation.code for violation in violations]
