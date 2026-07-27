from pathlib import Path
from typing import Any, Dict

class SiteConfigError(ValueError):
    """Raised when ``site_config.json`` exists but cannot be parsed."""


def load_site_config(cwd: Path) -> Dict[str, Any]:
    """Load the project configuration without silently discarding bad input.

    A malformed configuration used to be treated as an empty one.  The next
    sync then wrote default values into ``.env`` and generated a project with
    the wrong settings, which is much harder to recover from than a clear
    error at the configuration boundary.
    """
    config_path = cwd / "site_config.json"
    if config_path.exists():
        import json

        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SiteConfigError(
                f"Unable to parse {config_path}: {exc}"
            ) from exc
        if not isinstance(config, dict):
            raise SiteConfigError(
                f"{config_path} must contain a JSON object at its top level."
            )
        return config
    return {}
