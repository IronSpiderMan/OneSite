from pathlib import Path
from typing import Any, Dict

from rich.console import Console

console = Console()


def sync_env_files(config: Dict[str, Any], backend_path: Path, frontend_path: Path):
    backend_env = backend_path / ".env"
    env_content = ""
    if backend_env.exists():
        env_content = backend_env.read_text()

    new_keys = {
        "PROJECT_NAME": config.get("project_name"),
        "DATABASE_URI": config.get("database_url"),
        "SECRET_KEY": config.get("secret_key"),
        "FIRST_SUPERUSER": config.get("first_superuser", "admin@example.com"),
        "FIRST_SUPERUSER_PASSWORD": config.get("first_superuser_password", "admin"),
    }

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
                updated_lines.append(f"{key}={new_keys[key]}")
                del new_keys[key]
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)

    for key, val in new_keys.items():
        updated_lines.append(f"{key}={val}")

    backend_path.mkdir(parents=True, exist_ok=True)
    backend_env.write_text("\n".join(updated_lines))
    console.print("Synced backend .env")

    frontend_env = frontend_path / ".env"
    api_url = config.get("api_url", "/api/v1")

    f_env_content = ""
    if frontend_env.exists():
        f_env_content = frontend_env.read_text()

    if "VITE_API_URL" not in f_env_content:
        frontend_path.mkdir(parents=True, exist_ok=True)
        with frontend_env.open("a") as f:
            f.write(f"\nVITE_API_URL={api_url}\n")
        console.print("Updated frontend .env with VITE_API_URL")
    else:
        lines = f_env_content.splitlines()
        updated_lines = []
        for line in lines:
            if line.startswith("VITE_API_URL="):
                updated_lines.append(f"VITE_API_URL={api_url}")
            else:
                updated_lines.append(line)
        frontend_env.write_text("\n".join(updated_lines))
        console.print(f"Updated frontend .env VITE_API_URL to {api_url}")

