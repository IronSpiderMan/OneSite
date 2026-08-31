"""Synchronization and router discovery for developer-owned backend code."""

from __future__ import annotations

import ast
from pathlib import Path

from ..project_paths import get_project_paths
from .assets import _mirror_source_tree


class CustomBackendError(ValueError):
    """Raised when custom backend source cannot be imported safely."""


def _ensure_python_packages(root: Path) -> None:
    """Make custom source directories explicit Python packages."""
    root.mkdir(parents=True, exist_ok=True)
    for directory in [root, *(path for path in root.rglob("*") if path.is_dir())]:
        if "__pycache__" not in directory.parts:
            (directory / "__init__.py").touch(exist_ok=True)


def _defines_router(path: Path) -> bool:
    """Return whether a module directly assigns a top-level ``router``."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise CustomBackendError(f"Invalid custom API module {path}: {exc}") from exc

    for statement in tree.body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "router"
            for target in statement.targets
        ):
            return True
        if (
            isinstance(statement, ast.AnnAssign)
            and isinstance(statement.target, ast.Name)
            and statement.target.id == "router"
        ):
            return True
    return False


def _discover_api_modules(api_source: Path) -> list[str]:
    modules: list[str] = []
    for path in sorted(api_source.rglob("*.py")):
        if path.name == "__init__.py" or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(api_source).with_suffix("")
        if not all(part.isidentifier() for part in relative.parts):
            raise CustomBackendError(
                f"Custom API path must use valid Python identifiers: {relative}"
            )
        if _defines_router(path):
            modules.append(".".join(relative.parts))
    return modules


def sync_custom_backend(cwd: Path, backend_path: Path) -> list[str]:
    """Mirror custom API/service/CRUD trees and return API router modules.

    Developer source is kept under ``app/backend``. Generated copies live in a
    ``custom`` package so model generation and framework endpoints can never
    overwrite developer-owned modules with the same filename.
    """
    source_root = get_project_paths(cwd).backend_source
    mappings = {
        "api": backend_path / "app" / "api" / "endpoints" / "custom",
        "services": backend_path / "app" / "services" / "custom",
        "cruds": backend_path / "app" / "cruds" / "custom",
    }

    for name, destination in mappings.items():
        source = source_root / name
        if source.exists():
            _ensure_python_packages(source)
        _mirror_source_tree(source, destination, f"custom backend {name}")

    api_source = source_root / "api"
    return _discover_api_modules(api_source) if api_source.exists() else []
