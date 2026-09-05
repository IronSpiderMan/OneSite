"""File writes and source-tree mirroring with content-aware status logging.

Every write compares the new content against the existing file (if any)
and logs one of three statuses: ``created``, ``updated``, or ``skipped``.
"""

import shutil
from pathlib import Path

from rich.console import Console

console = Console()


def write_file_with_status(path: Path, content: str) -> str:
    """Write *content* to *path*, comparing against any existing file.

    Returns one of ``"created"``, ``"updated"``, ``"skipped"``.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        path.write_text(content, encoding="utf-8")
        console.print(f"[green]Created {path}[/green]")
        return "created"

    existing = path.read_text(encoding="utf-8")
    if existing == content:
        console.print(f"[dim]Skipped {path} (unchanged)[/dim]")
        return "skipped"

    path.write_text(content, encoding="utf-8")
    console.print(f"[yellow]Updated {path}[/yellow]")
    return "updated"


def copy_file_with_status(src: Path, dst: Path) -> str:
    """Copy *src* to *dst*, comparing content before overwriting.

    Returns one of ``"created"``, ``"updated"``, ``"skipped"``.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    new_content = src.read_bytes()

    if not dst.exists():
        shutil.copy2(src, dst)
        console.print(f"[green]Created {dst}[/green]")
        return "created"

    existing = dst.read_bytes()
    if existing == new_content:
        console.print(f"[dim]Skipped {dst} (unchanged)[/dim]")
        return "skipped"

    shutil.copy2(src, dst)
    console.print(f"[yellow]Updated {dst}[/yellow]")
    return "updated"


def mirror_python_tree(source: Path, destination: Path) -> None:
    """Mirror Python source files without treating the generated copy as source."""
    destination.mkdir(parents=True, exist_ok=True)
    desired = {
        path.relative_to(source): path
        for path in source.rglob("*.py")
        if path.is_file()
    }

    for existing in sorted(destination.rglob("*.py")):
        relative = existing.relative_to(destination)
        if relative not in desired:
            existing.unlink()
            console.print(
                f"[yellow]Removed stale generated MQTT source {existing}[/yellow]"
            )

    for relative, source_file in sorted(desired.items()):
        copy_file_with_status(source_file, destination / relative)


def mirror_source_tree(source: Path, destination: Path, label: str) -> None:
    """Mirror a developer-owned source tree into generated backend output."""
    desired = {}
    if source.exists():
        desired = {
            path.relative_to(source): path
            for path in source.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
        }

    if destination.exists():
        for existing in sorted(
            (path for path in destination.rglob("*") if path.is_file()),
            reverse=True,
        ):
            relative = existing.relative_to(destination)
            if relative not in desired:
                existing.unlink()
                console.print(
                    f"[yellow]Removed stale generated {label} file {existing}[/yellow]"
                )

        for directory in sorted(
            (path for path in destination.rglob("*") if path.is_dir()),
            reverse=True,
        ):
            if not any(directory.iterdir()):
                directory.rmdir()

    for relative, source_file in sorted(desired.items()):
        copy_file_with_status(source_file, destination / relative)
