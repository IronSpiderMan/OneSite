"""File write utilities with content-aware status logging.

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
        path.write_text(content)
        console.print(f"[green]Created {path}[/green]")
        return "created"

    existing = path.read_text()
    if existing == content:
        console.print(f"[dim]Skipped {path} (unchanged)[/dim]")
        return "skipped"

    path.write_text(content)
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
