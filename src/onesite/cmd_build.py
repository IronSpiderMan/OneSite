"""Build developer-owned command projects during ``site sync``."""

import os
import shutil
import subprocess
from pathlib import Path

from rich.console import Console

from .project_paths import get_project_paths

console = Console()


class CommandBuildError(RuntimeError):
    """Raised when a command project cannot produce its expected executable."""


def _build_script(project_dir: Path) -> Path | None:
    """Return the build script for the current platform, if one exists."""
    script_name = "build.bat" if os.name == "nt" else "build.sh"
    script = project_dir / script_name
    return script if script.is_file() else None


def _build_command(script: Path) -> list[str]:
    if os.name == "nt":
        return ["cmd.exe", "/d", "/s", "/c", script.name]
    return ["sh", script.name]


def _find_executable(project_dir: Path) -> Path | None:
    """Find the platform-appropriate project-root executable."""
    project_name = project_dir.name
    candidate_names = (
        (f"{project_name}.exe", project_name)
        if os.name == "nt"
        else (project_name, f"{project_name}.exe")
    )
    for candidate_name in candidate_names:
        candidate = project_dir / candidate_name
        if candidate.is_file():
            return candidate
    return None


def build_command_projects(root: Path) -> list[Path]:
    """Build ``app/cmd/*`` projects and copy their executables to backend/bin.

    Each immediate child directory is treated as one command project. Projects
    without a build script for the current platform are skipped.
    """
    paths = get_project_paths(root)
    commands_dir = paths.cmd
    if not commands_dir.is_dir():
        console.print(f"[dim]No command projects found at {commands_dir}; skipping.[/dim]")
        return []

    destination_dir = paths.backend / "bin"
    copied: list[Path] = []

    for project_dir in sorted(commands_dir.iterdir(), key=lambda path: path.name):
        if not project_dir.is_dir():
            continue

        script = _build_script(project_dir)
        if script is None:
            console.print(
                f"[dim]Skipping command project {project_dir.name}: "
                "no build script for this platform.[/dim]"
            )
            continue

        console.print(f"[blue]Building command project {project_dir.name}...[/blue]")
        try:
            subprocess.run(_build_command(script), cwd=project_dir, check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise CommandBuildError(
                f"Command project {project_dir.name!r} failed to build: {exc}"
            ) from exc

        executable = _find_executable(project_dir)
        if executable is None:
            expected = project_dir / project_dir.name
            if os.name == "nt":
                expected = expected.with_suffix(".exe")
            raise CommandBuildError(
                f"Command project {project_dir.name!r} did not produce {expected}."
            )

        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / executable.name
        shutil.copy2(executable, destination)
        copied.append(destination)
        console.print(f"[green]Copied command executable to {destination}[/green]")

    return copied
