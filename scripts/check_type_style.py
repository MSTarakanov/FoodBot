#!/usr/bin/env python3
from __future__ import annotations

import ast
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Violation:
    path: Path
    line: int
    column: int
    code: str
    message: str

    def format(self) -> str:
        return f"{self.path}:{self.line}:{self.column}: {self.code} {self.message}"


class TypeStyleChecker(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.violations: list[Violation] = []
        self.any_names = {"Any"}
        self.optional_names = {"Optional"}
        self.union_names = {"Union"}
        self.typing_module_names = {"typing"}

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "typing":
                self.typing_module_names.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "typing":
            for alias in node.names:
                imported_name = alias.asname or alias.name
                if alias.name == "Any":
                    self.any_names.add(imported_name)
                    self._add_violation(
                        node,
                        "TYP001",
                        "Do not use typing.Any in src.",
                    )
                elif alias.name == "Optional":
                    self.optional_names.add(imported_name)
                elif alias.name == "Union":
                    self.union_names.add(imported_name)
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        if node.annotation is not None:
            self._check_annotation(node.annotation)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.returns is not None:
            self._check_annotation(node.returns)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if node.returns is not None:
            self._check_annotation(node.returns)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._check_annotation(node.annotation)
        self.generic_visit(node)

    def visit_TypeAlias(self, node: ast.TypeAlias) -> None:
        self._check_annotation(node.value)
        self.generic_visit(node)

    def _check_annotation(self, node: ast.AST) -> None:
        if self._is_any(node):
            self._add_violation(node, "TYP001", "Do not use typing.Any in src.")
            return

        union_members = self._union_members(node)
        if union_members:
            self._check_union_members(node, union_members)
            for member in union_members:
                self._check_annotation(member)
            return

        if self._is_optional_subscript(node):
            for member in self._subscript_items(node):
                self._check_annotation(member)
            return

        for child in ast.iter_child_nodes(node):
            self._check_annotation(child)

    def _check_union_members(self, node: ast.AST, members: list[ast.AST]) -> None:
        non_none_members = [member for member in members if not self._is_none(member)]
        if len(members) == 2 and len(non_none_members) == 1:
            return

        self._add_violation(
            node,
            "TYP002",
            "Only optional unions are allowed in src: use T | None, not A | B.",
        )

    def _union_members(self, node: ast.AST) -> list[ast.AST]:
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return [
                *self._union_operand_members(node.left),
                *self._union_operand_members(node.right),
            ]

        if self._is_union_subscript(node):
            members: list[ast.AST] = []
            for item in self._subscript_items(node):
                members.extend(self._union_operand_members(item))
            return members

        return []

    def _union_operand_members(self, node: ast.AST) -> list[ast.AST]:
        return self._union_members(node) or [node]

    def _is_union_subscript(self, node: ast.AST) -> bool:
        return isinstance(node, ast.Subscript) and (
            self._is_name(node.value, self.union_names)
            or self._is_typing_attribute(node.value, "Union")
        )

    def _is_optional_subscript(self, node: ast.AST) -> bool:
        return isinstance(node, ast.Subscript) and (
            self._is_name(node.value, self.optional_names)
            or self._is_typing_attribute(node.value, "Optional")
        )

    def _subscript_items(self, node: ast.AST) -> list[ast.AST]:
        if not isinstance(node, ast.Subscript):
            return []
        if isinstance(node.slice, ast.Tuple):
            return list(node.slice.elts)
        return [node.slice]

    def _is_any(self, node: ast.AST) -> bool:
        return self._is_name(node, self.any_names) or self._is_typing_attribute(node, "Any")

    def _is_none(self, node: ast.AST) -> bool:
        return isinstance(node, ast.Constant) and node.value is None

    def _is_name(self, node: ast.AST, names: set[str]) -> bool:
        return isinstance(node, ast.Name) and node.id in names

    def _is_typing_attribute(self, node: ast.AST, name: str) -> bool:
        return (
            isinstance(node, ast.Attribute)
            and node.attr == name
            and self._is_name(node.value, self.typing_module_names)
        )

    def _add_violation(self, node: ast.AST, code: str, message: str) -> None:
        self.violations.append(
            Violation(
                path=self.path,
                line=getattr(node, "lineno", 1),
                column=getattr(node, "col_offset", 0) + 1,
                code=code,
                message=message,
            )
        )


def check_file(path: Path) -> list[Violation]:
    checker = TypeStyleChecker(path)
    checker.visit(ast.parse(path.read_text(), filename=str(path), type_comments=True))
    return checker.violations


def python_files(paths: Iterable[Path]) -> tuple[Path, ...]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
        elif path.suffix == ".py":
            files.append(path)
    return tuple(files)


def main(argv: list[str]) -> int:
    paths = tuple(Path(arg) for arg in argv[1:]) or (Path("src"),)
    violations = [
        violation
        for path in python_files(paths)
        for violation in check_file(path)
    ]

    if not violations:
        return 0

    for violation in violations:
        print(violation.format(), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
