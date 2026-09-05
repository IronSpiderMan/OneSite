"""Remove generator-only metadata and imports from generated model files."""

from __future__ import annotations

import ast
from pathlib import Path

from ..file_utils import write_file_with_status


class StandaloneModelError(ValueError):
    """Raised when a generated model still needs the OneSite generator."""


def _is_onesite_metadata_assignment(node: ast.AST) -> bool:
    if isinstance(node, ast.Assign):
        return any(
            isinstance(target, ast.Name) and target.id == "__onesite__"
            for target in node.targets
        )
    return (
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "__onesite__"
    )


def _remove_line_ranges(source: str, ranges: list[tuple[int, int]]) -> str:
    lines = source.splitlines(keepends=True)
    for start, end in sorted(ranges, reverse=True):
        del lines[start - 1 : end]
    return "".join(lines)


def _replace_metadata_with_pass(source: str, ranges: list[tuple[int, int]]) -> str:
    """Remove metadata expressions while keeping otherwise-empty classes valid."""

    lines = source.splitlines(keepends=True)
    for start, end in sorted(ranges, reverse=True):
        original = lines[start - 1]
        indentation = original[: len(original) - len(original.lstrip())]
        newline = "\n" if original.endswith("\n") else ""
        lines[start - 1 : end] = [f"{indentation}pass{newline}"]
    return "".join(lines)


def _strip_generator_metadata(path: Path) -> None:
    source = path.read_text(encoding="utf-8").replace(
        "from onesite_runtime import",
        "from app.core.action_runtime import",
    ).replace(
        "import onesite_runtime",
        "from app.core import action_runtime as onesite_runtime",
    )
    tree = ast.parse(source, filename=str(path))
    metadata_ranges: list[tuple[int, int]] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef, ast.FunctionDef)):
            for statement in node.body:
                if _is_onesite_metadata_assignment(statement):
                    metadata_ranges.append((statement.lineno, statement.end_lineno or statement.lineno))

    standalone_source = _replace_metadata_with_pass(source, metadata_ranges)
    standalone_tree = ast.parse(standalone_source, filename=str(path))
    import_ranges: list[tuple[int, int]] = []

    for node in standalone_tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "onesite.config":
            imported_names = {alias.asname or alias.name for alias in node.names}
        elif isinstance(node, ast.Import):
            config_aliases = [alias for alias in node.names if alias.name == "onesite.config"]
            if len(config_aliases) != len(node.names):
                continue
            imported_names = {alias.asname or "onesite" for alias in config_aliases}
        else:
            continue
        remaining_names = {
            child.id
            for child in ast.walk(standalone_tree)
            if isinstance(child, ast.Name)
            and isinstance(child.ctx, ast.Load)
            and child.id in imported_names
        }
        if remaining_names:
            names = ", ".join(sorted(remaining_names))
            raise StandaloneModelError(
                f"{path} uses OneSite config symbol(s) outside __onesite__: {names}. "
                "OneSite config objects are build-time metadata and cannot be used by "
                "the generated application at runtime."
            )
        import_ranges.append((node.lineno, node.end_lineno or node.lineno))

    standalone_source = _remove_line_ranges(standalone_source, import_ranges)
    if "from onesite" in standalone_source or "import onesite" in standalone_source:
        raise StandaloneModelError(
            f"{path} still imports OneSite. Generated model code may only use "
            "application/runtime dependencies."
        )
    write_file_with_status(path, standalone_source)


def phase_finalize_standalone(backend_path: Path) -> None:
    """Make generated backend models independent of the OneSite package."""

    models_dir = backend_path / "app" / "models"
    for model_path in sorted(models_dir.rglob("*.py")):
        if model_path.name != "__init__.py":
            _strip_generator_metadata(model_path)
