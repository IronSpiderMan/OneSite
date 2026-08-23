"""Isolation boundary for importing generated project model modules."""

from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType

from sqlmodel import SQLModel


class ModelIntrospectionError(RuntimeError):
    """Raised when generated project models cannot be imported or introspected."""


def _is_project_module(module_name: str) -> bool:
    return module_name == "app" or module_name.startswith("app.")


@contextmanager
def isolated_project_imports(backend_path: Path) -> Iterator[None]:
    """Temporarily load ``app.*`` modules exclusively from one generated backend.

    CLI runners and test processes may generate more than one project in the
    same interpreter.  Restoring both ``sys.path`` and any pre-existing
    ``app.*`` modules prevents one project from leaking into the next.
    """
    original_path = list(sys.path)
    previous_modules: dict[str, ModuleType] = {
        name: module
        for name, module in sys.modules.items()
        if _is_project_module(name)
    }
    existing_tables = set(SQLModel.metadata.tables)
    for name in previous_modules:
        sys.modules.pop(name, None)

    sys.path.insert(0, str(backend_path.resolve()))
    importlib.invalidate_caches()
    try:
        yield
    finally:
        for table_name in set(SQLModel.metadata.tables) - existing_tables:
            SQLModel.metadata.remove(SQLModel.metadata.tables[table_name])
        for name in tuple(sys.modules):
            if _is_project_module(name):
                sys.modules.pop(name, None)
        sys.modules.update(previous_modules)
        sys.path[:] = original_path
        importlib.invalidate_caches()
