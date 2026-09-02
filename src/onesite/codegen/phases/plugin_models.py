"""Materialize generated models required by enabled plugins.

Plugin models live only in generated output.  They must be created after the
source-model mirror has removed stale files and before model introspection
imports the generated package.
"""

from pathlib import Path

from ...project_paths import get_project_paths
from ..render import generate_file


_PLUGIN_MODEL_TEMPLATES = {
    "site_logger": (("app_log.py.j2", "app_log.py"),),
    "device_timeseries": (
        ("device_model.py.j2", "device_model.py"),
        ("device_model_field.py.j2", "device_model_field.py"),
        ("device.py.j2", "device.py"),
        ("device_field.py.j2", "device_field.py"),
        ("device_history.py.j2", "device_history.py"),
        ("device_history_latest.py.j2", "device_history_latest.py"),
    ),
}


def phase_generate_plugin_models(
    site_config: dict,
    cwd: Path,
    backend_path: Path,
) -> None:
    """Generate default plugin models unless the project provides an override."""
    enabled_plugins = site_config.get("plugins", [])
    source_models = get_project_paths(cwd).models
    generated_models = backend_path / "app" / "models"

    for plugin_name, model_templates in _PLUGIN_MODEL_TEMPLATES.items():
        if plugin_name not in enabled_plugins:
            continue
        for template_name, filename in model_templates:
            if (source_models / filename).exists():
                continue
            generate_file(template_name, {}, generated_models / filename)
