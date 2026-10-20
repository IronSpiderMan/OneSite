"""Regression coverage for generator safety boundaries."""

import json

import pytest

from onesite.codegen.config import SiteConfigError, load_site_config
from onesite.codegen.phases.sync_models import phase_sync_models


def test_invalid_site_config_fails_instead_of_using_and_writing_defaults(tmp_path):
    """A syntax error must not be converted into a destructive empty config."""
    (tmp_path / "site_config.json").write_text("{not valid json", encoding="utf-8")

    with pytest.raises(SiteConfigError, match="Unable to parse"):
        load_site_config(tmp_path)


def test_site_config_must_be_a_json_object(tmp_path):
    (tmp_path / "site_config.json").write_text(json.dumps(["not", "a", "config"]), encoding="utf-8")

    with pytest.raises(SiteConfigError, match="JSON object"):
        load_site_config(tmp_path)


def test_typed_python_site_config_is_normalized_for_existing_codegen(tmp_path):
    (tmp_path / "site_config.py").write_text(
        "from onesite.config import MqttCallback, MqttConfig, SiteConfig\n"
        "config = SiteConfig(\n"
        "    project_name='typed-demo',\n"
        "    mqtt=MqttConfig(callbacks=[MqttCallback(topic='device/#', handler='on_device')]),\n"
        ")\n",
        encoding="utf-8",
    )

    config = load_site_config(tmp_path)

    assert config["project_name"] == "typed-demo"
    assert config["mqtt"]["callbacks"] == [
        {"topic": "device/#", "handler": "on_device", "qos": 1}
    ]


def test_python_site_config_requires_a_typed_config_export(tmp_path):
    (tmp_path / "site_config.py").write_text("config = {}\n", encoding="utf-8")

    with pytest.raises(SiteConfigError, match="config = SiteConfig"):
        load_site_config(tmp_path)


def test_python_and_json_config_cannot_coexist(tmp_path):
    (tmp_path / "site_config.py").write_text(
        "from onesite.config import SiteConfig\nconfig = SiteConfig()\n",
        encoding="utf-8",
    )
    (tmp_path / "site_config.json").write_text("{}", encoding="utf-8")

    with pytest.raises(SiteConfigError, match="Both site_config.py and site_config.json"):
        load_site_config(tmp_path)


def test_likely_misnamed_python_config_fails_with_rename_instruction(tmp_path):
    (tmp_path / "site_sync.py").write_text(
        "from onesite.config import SiteConfig\nconfig = SiteConfig()\n",
        encoding="utf-8",
    )

    with pytest.raises(SiteConfigError, match="must be named site_config.py"):
        load_site_config(tmp_path)


def test_model_sync_removes_models_deleted_from_the_source_directory(tmp_path):
    """Generated backend models mirror their source directory on every sync."""
    models_dir = tmp_path / "app" / "models"
    models_dir.mkdir(parents=True)
    (models_dir / "inventory.py").write_text("# current model\n", encoding="utf-8")

    backend_path = tmp_path / "generated" / "backend"
    destination = backend_path / "app" / "models"
    destination.mkdir(parents=True)
    (destination / "retired.py").write_text("# stale generated model\n", encoding="utf-8")

    phase_sync_models(tmp_path, backend_path)

    assert not (destination / "retired.py").exists()
    assert (destination / "inventory.py").read_text(encoding="utf-8") == "# current model\n"
    # Built-in models remain available when they have no project override.
    assert (destination / "user.py").exists()


def test_model_sync_recursively_mirrors_python_support_packages(tmp_path):
    """Models may import enums and helpers from nested Python packages."""
    models_dir = tmp_path / "app" / "models"
    enums_dir = models_dir / "enums"
    enums_dir.mkdir(parents=True)
    (models_dir / "alarm.py").write_text(
        "from .enums.alarm import Level\n",
        encoding="utf-8",
    )
    (enums_dir / "__init__.py").write_text("", encoding="utf-8")
    (enums_dir / "alarm.py").write_text(
        "from enum import StrEnum\n\nclass Level(StrEnum):\n    HIGH = 'high'\n",
        encoding="utf-8",
    )

    backend_path = tmp_path / "generated" / "backend"
    destination = backend_path / "app" / "models"
    stale_package = destination / "legacy"
    stale_package.mkdir(parents=True)
    (stale_package / "helper.py").write_text("STALE = True\n", encoding="utf-8")

    phase_sync_models(tmp_path, backend_path)

    assert (destination / "enums" / "__init__.py").exists()
    assert (destination / "enums" / "alarm.py").read_text(encoding="utf-8").endswith(
        "HIGH = 'high'\n"
    )
    assert not stale_package.exists()
