"""Phase 1 — Configuration loading and environment setup."""

from pathlib import Path

from ..config import load_site_config
from ..envsync import sync_env_files
from .base import console


def phase_load_config(cwd: Path) -> tuple[dict, Path]:
    """Load site_config.json, set defaults, sync .env files.

    Returns (site_config, backend_path).
    """
    site_config = load_site_config(cwd)

    site_config.setdefault("project_name", "MyApp")
    site_config.setdefault("logo", "")
    site_config.setdefault("database_url", "sqlite:///./app.db")
    site_config.setdefault("upload_dir", "uploads")
    site_config.setdefault("secret_key", "changeme")
    site_config.setdefault("access_token_expire_minutes", 11520)
    site_config.setdefault(
        "allowed_origins",
        [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
    )

    backend_path = cwd / "backend"
    sync_env_files(site_config, backend_path, cwd / "frontend")
    return site_config, backend_path
