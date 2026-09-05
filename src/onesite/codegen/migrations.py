"""Keep migration history in developer source and mirror it for deployment."""

from pathlib import Path

from .file_utils import copy_file_with_status, write_file_with_status
from .render import TEMPLATE_DIR, generate_file, generate_file_if_missing


def generate_migrations(cwd: Path, backend: Path) -> None:
    source = cwd / "app" / "migrations"
    (source / "versions").mkdir(parents=True, exist_ok=True)
    write_file_with_status(source / "versions/.gitkeep", "")
    generate_file_if_missing("alembic_env.py.j2", {}, source / "env.py")
    script = source / "script.py.mako"
    if not script.exists():
        copy_file_with_status(TEMPLATE_DIR / "alembic_script.py.mako", script)
    for path in source.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            copy_file_with_status(path, backend / "migrations" / path.relative_to(source))
    (backend / "migrations" / "versions").mkdir(parents=True, exist_ok=True)
    write_file_with_status(backend / "migrations/versions/.gitkeep", "")
    generate_file("alembic.ini.j2", {}, backend / "alembic.ini")
