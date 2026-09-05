"""Stage generation and publish only validated, owned artifacts.

Runtime data, installed dependencies and unowned files are never swept. The
manifest records successful output; failed rendering never touches the project.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

MANIFEST = ".onesite-manifest.json"


def _files(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    }


def _legacy_artifacts(root: Path) -> set[str]:
    """Adopt only the old generator's documented replaceable code locations."""
    names: set[str] = set()
    for directory, pattern in (
        ("backend/app/models", "*.py"), ("backend/app/schemas", "*.py"),
        ("backend/app/cruds", "*.py"), ("backend/app/services", "*.py"),
        ("backend/app/api/endpoints", "*.py"), ("backend/tests", "test_*_api.py"),
        ("frontend/src/pages", "*.tsx"), ("frontend/src/services", "*.ts"),
        ("frontend/src/stores", "*.ts"),
    ):
        for path in (root / directory).rglob(pattern):
            if "__pycache__" not in path.parts:
                names.add(path.relative_to(root).as_posix())
    return names


def _safe_path(root: Path, relative: str) -> Path:
    path = root / relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError(f"Invalid generated artifact path: {relative!r}")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Generated artifact escapes project through a symlink: {relative!r}")
    return path


def _replace(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".onesite-write-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(content)
        os.chmod(temporary, path.stat().st_mode if path.exists() else 0o644)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _publish(project: Path, staged: Path, source_before: dict[str, bytes]) -> None:
    generated = project / "generated"
    artifacts = _files(staged / "generated")
    # A full Python syntax pass must finish before publishing any files.
    for relative, content in artifacts.items():
        if relative.endswith(".py"):
            compile(content, relative, "exec")
    old_manifest = generated / MANIFEST
    previous = (
        set(json.loads(old_manifest.read_text())["files"])
        if old_manifest.exists() else _legacy_artifacts(generated)
    )
    changes: dict[Path, bytes | None] = {
        _safe_path(generated, relative): None for relative in previous - artifacts.keys()
    }
    for relative, content in artifacts.items():
        changes[_safe_path(generated, relative)] = content
    changes[old_manifest] = (json.dumps({"version": 1, "files": sorted(artifacts)}, indent=2) + "\n").encode()
    source_after = _files(staged / "app")
    for relative, content in source_after.items():
        if source_before.get(relative) != content:
            destination = _safe_path(project / "app", relative)
            actual = destination.read_bytes() if destination.exists() else None
            if actual != source_before.get(relative):
                raise RuntimeError(f"Source changed during sync: {destination}")
            changes[destination] = content
    originals: dict[Path, bytes | None] = {}
    new_modes = {
        _safe_path(generated, relative): (staged / "generated" / relative).stat().st_mode
        for relative in artifacts
    }
    new_modes.update({
        _safe_path(project / "app", relative): (staged / "app" / relative).stat().st_mode
        for relative in source_after
    })
    try:
        for path, content in changes.items():
            existing = path.read_bytes() if path.exists() else None
            if existing == content:
                continue
            originals[path] = existing
            if content is None:
                path.unlink(missing_ok=True)
            else:
                _replace(path, content)
                if existing is None and path in new_modes:
                    os.chmod(path, new_modes[path])
    except BaseException:
        for path, content in reversed(list(originals.items())):
            if content is None:
                path.unlink(missing_ok=True)
            else:
                _replace(path, content)
        raise


@contextmanager
def staged_generation(project: Path):
    lock = project / ".onesite-sync.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RuntimeError("Another sync is running (.onesite-sync.lock exists)") from exc
    os.close(descriptor)
    previous_cwd = Path.cwd()
    try:
        with tempfile.TemporaryDirectory(prefix=".onesite-sync-", dir=project) as temporary:
            staged = Path(temporary) / "project"
            shutil.copytree(project, staged, ignore=shutil.ignore_patterns(
                "generated", ".git", ".venv", "node_modules", "__pycache__",
                ".pytest_cache", ".ruff_cache", ".onesite-sync.lock",
                ".onesite-sync-*",  # Exclude staging directories to avoid recursive copies.
            ))
            source_before = _files(staged / "app")
            templates = Path(__file__).resolve().parent.parent / "templates"
            for component in ("backend", "frontend"):
                destination = staged / "generated" / component
                shutil.copytree(templates / component, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                environment = project / "generated" / component / ".env"
                if environment.exists():
                    shutil.copy2(environment, destination / ".env")
            os.chdir(staged)
            yield staged
            os.chdir(previous_cwd)
            _publish(project, staged, source_before)
    finally:
        os.chdir(previous_cwd)
        lock.unlink(missing_ok=True)
