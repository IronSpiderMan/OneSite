from pathlib import Path
from typing import Any, Dict

from .file_utils import write_file_with_status
from .theme import resolve_theme


def _env_value(value: Any) -> str:
    """Serialize a site config value into a pydantic-settings friendly value."""
    if isinstance(value, (dict, list)):
        import json

        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def sync_env_files(config: Dict[str, Any], backend_path: Path, frontend_path: Path):
    backend_env = backend_path / ".env"
    env_content = ""
    if backend_env.exists():
        env_content = backend_env.read_text(encoding="utf-8")

    new_keys = {
        "PROJECT_NAME": config.get("project_name"),
        "DATABASE_URI": config.get("database_url"),
        "SECRET_KEY": config.get("secret_key"),
        "FIRST_SUPERUSER": config.get("first_superuser", "admin@example.com"),
        "FIRST_SUPERUSER_PASSWORD": config.get("first_superuser_password", "admin"),
    }

    # ``extra`` is the generic escape hatch for backend settings. Keep every
    # entry available for runtime overrides instead of only baking the values
    # into the generated Settings class.
    extra = config.get("extra", {})
    if isinstance(extra, dict):
        new_keys.update(extra)

    if config.get("redis"):
        redis_cfg = config["redis"]
        if isinstance(redis_cfg, dict):
            new_keys["REDIS_URL"] = redis_cfg.get("url", "redis://localhost:6379/0")
            if redis_cfg.get("password"):
                new_keys["REDIS_PASSWORD"] = redis_cfg["password"]

    if config.get("rabbitmq"):
        mq_cfg = config["rabbitmq"]
        if isinstance(mq_cfg, dict):
            new_keys["RABBITMQ_URL"] = mq_cfg.get("url", "amqp://guest:guest@localhost:5672/")

    if config.get("mqtt"):
        mqtt_cfg = config["mqtt"]
        if isinstance(mqtt_cfg, dict):
            new_keys["MQTT_URL"] = mqtt_cfg.get("url", "mqtt://localhost:1883")
            if mqtt_cfg.get("username"):
                new_keys["MQTT_USERNAME"] = mqtt_cfg["username"]
            if mqtt_cfg.get("password"):
                new_keys["MQTT_PASSWORD"] = mqtt_cfg["password"]
            if mqtt_cfg.get("client_id"):
                new_keys["MQTT_CLIENT_ID"] = mqtt_cfg["client_id"]

    if config.get("kafka"):
        kafka_cfg = config["kafka"]
        if isinstance(kafka_cfg, dict):
            new_keys["KAFKA_BROKERS"] = kafka_cfg.get(
                "brokers", ["localhost:9092"]
            )
            callbacks = kafka_cfg.get("callbacks", [])
            if isinstance(callbacks, list):
                for index, callback in enumerate(callbacks):
                    if not isinstance(callback, dict):
                        continue
                    new_keys[f"KAFKA_CALLBACK_{index}_TOPIC"] = callback.get(
                        "topic", ""
                    )
                    new_keys[f"KAFKA_CALLBACK_{index}_GROUP_ID"] = callback.get(
                        "group_id", "onesite_backend"
                    )

    import json

    allowed_origins = config.get("allowed_origins", [])
    if allowed_origins:
        new_keys["BACKEND_CORS_ORIGINS"] = json.dumps(allowed_origins)

    lines = env_content.splitlines()
    updated_lines = []
    for line in lines:
        if "=" in line and not line.startswith("#"):
            key, _ = line.split("=", 1)
            key = key.strip()
            if key in new_keys:
                updated_lines.append(f"{key}={_env_value(new_keys[key])}")
                del new_keys[key]
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)

    for key, val in new_keys.items():
        updated_lines.append(f"{key}={_env_value(val)}")

    write_file_with_status(backend_env, "\n".join(updated_lines))

    frontend_env = frontend_path / ".env"
    project_name = config.get("project_name", "OneSite")
    api_url = config.get("api_url", "/api/v1")
    default_theme = resolve_theme(config)[0]["id"]

    f_env_content = ""
    if frontend_env.exists():
        f_env_content = frontend_env.read_text(encoding="utf-8")

    logo = config.get("logo", "")
    # Ensure logo is an absolute path so it works from any route
    if logo and not logo.startswith(("/", "http://", "https://", "data:")):
        logo = f"/{logo}"

    logo_link = config.get("logo_link", "/dashboard")
    timezone = (
        extra.get("TIMEZONE", "Asia/Shanghai")
        if isinstance(extra, dict)
        else "Asia/Shanghai"
    )

    f_new_keys = {
        "VITE_PROJECT_NAME": project_name,
        "VITE_API_URL": api_url,
        "VITE_PROJECT_LOGO": logo,
        "VITE_LOGO_LINK": logo_link,
        "VITE_TIMEZONE": timezone,
        "VITE_DEFAULT_THEME": default_theme,
    }

    f_lines = f_env_content.splitlines()
    f_updated_lines = []
    for line in f_lines:
        if "=" in line and not line.startswith("#"):
            key, _ = line.split("=", 1)
            key = key.strip()
            if key in f_new_keys:
                f_updated_lines.append(f"{key}={f_new_keys[key]}")
                del f_new_keys[key]
            else:
                f_updated_lines.append(line)
        else:
            f_updated_lines.append(line)

    for key, val in f_new_keys.items():
        f_updated_lines.append(f"{key}={val}")

    write_file_with_status(frontend_env, "\n".join(f_updated_lines))

    # Desktop releases cannot use Vite's development proxy. Bake the absolute
    # FastAPI endpoint into the Tauri-specific Vite mode instead.
    desktop = config.get("desktop", {})
    desktop_env = frontend_path / ".env.desktop"
    desktop_env_content = (
        "# Generated by OneSite; configure values under desktop in site_config.py.\n"
        "VITE_DESKTOP=true\n"
        f"VITE_API_URL={desktop.get('api_url', 'http://127.0.0.1:8000/api/v1')}\n"
        f"VITE_PROJECT_NAME={project_name}\n"
        f"VITE_PROJECT_LOGO={logo}\n"
        f"VITE_LOGO_LINK={logo_link}\n"
        f"VITE_TIMEZONE={timezone}\n"
        f"VITE_DEFAULT_THEME={default_theme}\n"
    )
    write_file_with_status(desktop_env, desktop_env_content)
