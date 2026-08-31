"""Canonical paths for OneSite projects."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    source: Path
    models: Path
    integrations: Path
    tools: Path
    tasks: Path
    cmd: Path
    backend_source: Path
    frontend_source: Path
    generated: Path
    backend: Path
    frontend: Path
    deploy: Path


def get_project_paths(root: Path) -> ProjectPaths:
    """Resolve the developer-owned source and generated output directories.

    OneSite projects always use ``app/`` for source and ``generated/`` for
    replaceable output. Top-level ``models/``, ``backend/``, and ``frontend/``
    directories are not project paths.
    """
    root = root.resolve()
    source = root / "app"
    generated = root / "generated"
    return ProjectPaths(
        root=root,
        source=source,
        models=source / "models",
        integrations=source / "integrations",
        tools=source / "tools",
        tasks=source / "tasks",
        cmd=source / "cmd",
        backend_source=source / "backend",
        frontend_source=source / "frontend",
        generated=generated,
        backend=generated / "backend",
        frontend=generated / "frontend",
        deploy=root / "deploy",
    )
