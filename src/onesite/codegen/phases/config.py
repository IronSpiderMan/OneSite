"""Phase 1 — Configuration loading and environment setup."""

from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..config import (
    SiteConfigError,
    load_site_config,
    validate_mqtt_config,
    validate_kafka_config,
    validate_navigation_config,
    validate_desktop_config,
    validate_external_resource_providers_config,
    validate_scheduled_tasks_config,
    validate_task_center_config,
    validate_tools_config,
    validate_video_stream_config,
)
from ..envsync import sync_env_files
from ...project_paths import get_project_paths


def phase_load_config(cwd: Path) -> tuple[dict, Path]:
    """Load project configuration, set defaults, sync .env files.

    Returns (site_config, backend_path).
    """
    site_config = load_site_config(cwd)

    site_config.setdefault("project_name", "MyApp")
    site_config.setdefault("logo", "")
    site_config.setdefault("logo_link", "/dashboard")
    site_config.setdefault("database_url", "sqlite:///./app.db")
    site_config.setdefault("upload_dir", "uploads")
    site_config.setdefault("secret_key", "changeme")
    site_config.setdefault("access_token_expire_minutes", 11520)
    extra = site_config.setdefault("extra", {})
    if not isinstance(extra, dict):
        raise SiteConfigError("site_config.json field 'extra' must be a JSON object.")
    timezone_name = extra.setdefault("TIMEZONE", "Asia/Shanghai")
    if not isinstance(timezone_name, str):
        raise SiteConfigError("site_config.json field 'extra.TIMEZONE' must be a string.")
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise SiteConfigError(
            f"site_config.json field 'extra.TIMEZONE' is not a valid IANA timezone: {timezone_name!r}."
        ) from exc
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
    validate_desktop_config(site_config)
    validate_external_resource_providers_config(site_config)
    allowed_origins = site_config["allowed_origins"]
    if not isinstance(allowed_origins, list) or any(
        not isinstance(origin, str) for origin in allowed_origins
    ):
        raise SiteConfigError(
            "site_config.json field 'allowed_origins' must be an array of strings."
        )
    # Tauri 2 serves release assets from these platform-specific origins.
    # Exact origins keep the API usable without opening CORS to arbitrary hosts.
    for desktop_origin in ("tauri://localhost", "http://tauri.localhost"):
        if desktop_origin not in allowed_origins:
            allowed_origins.append(desktop_origin)

    validate_mqtt_config(site_config)
    validate_kafka_config(site_config)
    validate_navigation_config(site_config)
    validate_tools_config(site_config)
    validate_scheduled_tasks_config(site_config)
    validate_task_center_config(site_config)
    validate_video_stream_config(site_config)

    paths = get_project_paths(cwd)
    backend_path = paths.backend
    sync_env_files(site_config, backend_path, paths.frontend)
    return site_config, backend_path
