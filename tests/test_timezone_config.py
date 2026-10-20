import json
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

from onesite.codegen.config import SiteConfigError
from onesite.codegen.phases.config import phase_load_config


TEMPLATE_DIR = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"


def test_extra_values_and_timezone_are_synced_to_env_files(tmp_path):
    config = {
        "project_name": "clock",
        "extra": {
            "TIMEZONE": "Europe/Paris",
            "FEATURE_ENABLED": True,
            "LIMITS": {"daily": 10},
        },
    }
    (tmp_path / "site_config.json").write_text(json.dumps(config), encoding="utf-8")

    loaded, _ = phase_load_config(tmp_path)

    backend_env = (tmp_path / "generated" / "backend" / ".env").read_text(encoding="utf-8")
    frontend_env = (tmp_path / "generated" / "frontend" / ".env").read_text(encoding="utf-8")
    assert loaded["extra"]["TIMEZONE"] == "Europe/Paris"
    assert "TIMEZONE=Europe/Paris" in backend_env
    assert "FEATURE_ENABLED=true" in backend_env
    assert 'LIMITS={"daily": 10}' in backend_env
    assert "VITE_TIMEZONE=Europe/Paris" in frontend_env


def test_timezone_defaults_to_shanghai(tmp_path):
    (tmp_path / "site_config.json").write_text("{}", encoding="utf-8")

    loaded, _ = phase_load_config(tmp_path)

    assert loaded["extra"]["TIMEZONE"] == "Asia/Shanghai"
    assert "TIMEZONE=Asia/Shanghai" in (tmp_path / "generated" / "backend" / ".env").read_text(encoding="utf-8")
    assert "VITE_TIMEZONE=Asia/Shanghai" in (tmp_path / "generated" / "frontend" / ".env").read_text(encoding="utf-8")


def test_invalid_timezone_fails_before_env_sync(tmp_path):
    config = {"extra": {"TIMEZONE": "Mars/Olympus_Mons"}}
    (tmp_path / "site_config.json").write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(SiteConfigError, match="valid IANA timezone"):
        phase_load_config(tmp_path)

    assert not (tmp_path / "generated" / "backend" / ".env").exists()


def test_scheduler_uses_configured_timezone():
    environment = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    scheduler = environment.get_template("scheduler.py.j2").render()
    datetime_helpers = environment.get_template("backend_datetime.py.j2").render()

    assert "AsyncIOScheduler(timezone=self._timezone)" in scheduler
    assert 'timezone=self._timezone' in scheduler
    assert "dt.astimezone(self._timezone)" in scheduler
    assert "value = value.replace(tzinfo=SYSTEM_TIMEZONE)" in datetime_helpers
    assert "return value.astimezone(timezone.utc)" in datetime_helpers
