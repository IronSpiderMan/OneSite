import keyword
from pathlib import Path
from typing import Any, Dict


class SiteConfigError(ValueError):
    """Raised when ``site_config.json`` exists but cannot be parsed."""


def validate_mqtt_config(config: Dict[str, Any]) -> None:
    """Validate and normalize the MQTT section used by code generation."""
    mqtt = config.get("mqtt")
    if mqtt is None:
        return
    if not isinstance(mqtt, dict):
        raise SiteConfigError("site_config.json field 'mqtt' must be a JSON object.")

    callbacks = mqtt.get("callbacks", [])
    if not isinstance(callbacks, list):
        raise SiteConfigError(
            "site_config.json field 'mqtt.callbacks' must be a JSON array."
        )

    seen: set[tuple[str, str]] = set()
    for index, callback in enumerate(callbacks):
        field = f"site_config.json field 'mqtt.callbacks[{index}]'"
        if not isinstance(callback, dict):
            raise SiteConfigError(f"{field} must be a JSON object.")

        topic = callback.get("topic")
        if not isinstance(topic, str) or not topic.strip():
            raise SiteConfigError(f"{field}.topic must be a non-empty string.")

        handler = callback.get("handler")
        if (
            not isinstance(handler, str)
            or not handler.isidentifier()
            or keyword.iskeyword(handler)
            or handler == "__init__"
        ):
            raise SiteConfigError(
                f"{field}.handler must be a valid Python identifier."
            )

        qos = callback.setdefault("qos", 1)
        if isinstance(qos, bool) or qos not in (0, 1, 2):
            raise SiteConfigError(f"{field}.qos must be 0, 1, or 2.")

        registration = (topic, handler)
        if registration in seen:
            raise SiteConfigError(
                f"{field} duplicates MQTT callback {topic!r} -> {handler!r}."
            )
        seen.add(registration)


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
