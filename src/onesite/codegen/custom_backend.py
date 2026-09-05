"""Synchronization and router discovery for developer-owned backend code."""

from __future__ import annotations

import ast
import keyword
import re
from pathlib import Path

from ..project_paths import get_project_paths
from .file_utils import mirror_source_tree
from .render import generate_file_if_missing


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


def _scaffold_custom_backend(source_root: Path, features: list[dict]) -> list[str]:
    modules: list[str] = []
    for feature in features:
        if feature.get("frontend_only"):
            continue
        name = feature["name"]
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name) or keyword.iskeyword(name):
            raise CustomBackendError(
                f"Custom feature name {name!r} must be a lowercase Python module name."
            )
        class_name = "".join(part.title() for part in name.split("_"))
        context = {
            "feature_name": name,
            "class_name": class_name,
            "api_path": name.replace("_", "-"),
        }
        generate_file_if_missing(
            "custom_feature_backend_crud.py.j2",
            context,
            source_root / "cruds" / f"{name}.py",
        )
        generate_file_if_missing(
            "custom_feature_backend_service.py.j2",
            context,
            source_root / "services" / f"{name}.py",
        )
        api_file = source_root / "api" / f"{name}.py"
        generate_file_if_missing(
            "custom_feature_backend_api.py.j2", context, api_file
        )
        if not _defines_router(api_file):
            raise CustomBackendError(
                f"Configured custom feature API {api_file} must define a top-level router."
            )
        modules.append(name)
    return modules


def sync_custom_backend(
    cwd: Path, backend_path: Path, features: list[dict] | None = None
) -> list[str]:
    """Mirror custom API/service/CRUD trees and return API router modules.

    Developer source is kept under ``app/backend``. Generated copies live in a
    ``custom`` package so model generation and framework endpoints can never
    overwrite developer-owned modules with the same filename.
    """
    source_root = get_project_paths(cwd).backend_source
    configured_modules = _scaffold_custom_backend(source_root, features or [])
    mappings = {
        "api": backend_path / "app" / "api" / "endpoints" / "custom",
        "services": backend_path / "app" / "services" / "custom",
        "cruds": backend_path / "app" / "cruds" / "custom",
    }

    for name, destination in mappings.items():
        source = source_root / name
        if source.exists():
            _ensure_python_packages(source)
        mirror_source_tree(source, destination, f"custom backend {name}")

    return configured_modules
