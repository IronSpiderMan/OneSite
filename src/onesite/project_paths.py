"""Canonical project paths with backward compatibility for legacy projects."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    source: Path
    models: Path
    integrations: Path
    generated: Path
    backend: Path
    frontend: Path
    deploy: Path
    modern: bool


def get_project_paths(root: Path, *, modern: bool | None = None) -> ProjectPaths:
    """Resolve source and generated directories for a OneSite project.

    New projects use ``app/`` for developer-owned source and ``generated/``
    for replaceable output. Existing projects with top-level
    ``models/backend/frontend`` keep their legacy paths.
    """
    root = root.resolve()
    if modern is None:
        modern = (root / "app").exists() or (root / "generated").exists()

    if modern:
        source = root / "app"
        generated = root / "generated"
        return ProjectPaths(
            root=root,
            source=source,
            models=source / "models",
            integrations=source / "integrations",
            generated=generated,
            backend=generated / "backend",
            frontend=generated / "frontend",
            deploy=root / "deploy",
            modern=True,
        )

    return ProjectPaths(
        root=root,
        source=root,
        models=root / "models",
        integrations=root / "integrations",
        generated=root,
        backend=root / "backend",
        frontend=root / "frontend",
        deploy=root / "deploy",
        modern=False,
    )
