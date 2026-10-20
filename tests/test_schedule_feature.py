"""The optional built-in schedule model and recurrence validation."""

from datetime import date
from pathlib import Path
import re

import pytest

from onesite.codegen.config import SiteConfigError, validate_schedule_config
from onesite.codegen.model_imports import isolated_project_imports
from onesite.codegen.phases.introspect_models import phase_introspect
from onesite.codegen.phases.schedule import phase_generate_schedule_model
from onesite.codegen.phases.sync_models import phase_sync_models
from onesite.config import ScheduleConfig, SiteConfig
from onesite.codegen.render import create_template_environment


def test_schedule_config_requires_a_target_and_display_field():
    assert SiteConfig(schedule=ScheduleConfig(enabled=True, target_model="Employee", display_field="name"))
    with pytest.raises(ValueError, match="target_model"):
        ScheduleConfig(enabled=True)
    with pytest.raises(SiteConfigError, match="display_field"):
        validate_schedule_config({"schedule": {"enabled": True, "target_model": "Employee"}})


def test_generated_schedule_rule_validation(tmp_path: Path):
    backend = tmp_path / "backend"
    models_dir = backend / "app" / "models"
    models_dir.mkdir(parents=True)
    (backend / "app" / "__init__.py").write_text("")
    (models_dir / "__init__.py").write_text("")
    (models_dir / "employee.py").write_text(
        "from sqlmodel import SQLModel, Field\n"
        "class Employee(SQLModel, table=True):\n"
        "    id: int | None = Field(default=None, primary_key=True)\n"
        "    name: str\n"
    )
    config = {"schedule": {"enabled": True, "target_model": "Employee", "display_field": "name"}}
    target = {
        "name": "Employee", "module_name": "employee", "source_module": "employee",
        "table_name": "employee", "primary_key_columns": ["id"], "id_type": "int",
        "role_permissions": {"user": "r", "admin": "crud", "developer": "crud"},
        "fields": [{"name": "name", "permissions": "r", "role_permissions": {
            "user": "r", "admin": "cru", "developer": "cru"
        }}],
    }
    assert phase_generate_schedule_model(config, [target], backend)
    with isolated_project_imports(backend):
        from app.models.schedule import MonthDay, Recurrence, Schedule, Shift, Weekday

        assert Schedule.__onesite__["actions"]["toggle_enabled"] == {
            "toggle": "enabled", "permissions": "da"
        }
        assert Schedule.model_fields["dates"].annotation == list[date]
        assert Schedule.model_fields["weekdays"].annotation == list[Weekday]
        assert Schedule.model_fields["month_days"].annotation == list[MonthDay]
        assert Schedule.model_validate({"target_id": 1, "weekdays": [0, 2], "month_days": [1, 31]}).weekdays == [Weekday.MONDAY, Weekday.WEDNESDAY]
        assert Schedule.model_validate({"target_id": 1, "weekdays": [0, 2], "month_days": [1, 31]}).month_days == [MonthDay.DAY_1, MonthDay.DAY_31]
        assert Schedule.__table__.c.dates.type.process_bind_param([date(2026, 9, 2)], None) == ["2026-09-02"]
        assert Schedule.__table__.c.dates.type.process_result_value(["2026-09-02"], None) == [date(2026, 9, 2)]
        assert Schedule.display_weekdays(None, [0, 2]) == ["周一", "周三"]
        assert Schedule.display_month_days(None, [1, 3]) == ["1日", "3日"]

        values = {
            "shift": Shift.DAY, "recurrence": Recurrence.WEEKLY,
            "start_date": date(2026, 9, 1), "end_date": None,
            "weekdays": [0, 2], "month_days": [], "dates": [],
        }
        Schedule._validate_rule(values)
        with pytest.raises(ValueError, match="weekdays"):
            Schedule._validate_rule({**values, "weekdays": [7]})
        with pytest.raises(ValueError, match="end_date"):
            Schedule._validate_rule({**values, "end_date": date(2026, 8, 31)})
        with pytest.raises(ValueError, match="specified dates"):
            Schedule._validate_rule({**values, "recurrence": Recurrence.DATES, "dates": ["2026-08-01"]})
        Schedule._validate_rule({**values, "recurrence": Recurrence.DATES, "dates": [date(2026, 9, 2)]})


def test_schedule_target_must_be_valid(tmp_path: Path):
    config = {"schedule": {"enabled": True, "target_model": "Missing", "display_field": "name"}}
    with pytest.raises(ValueError, match="target_model"):
        phase_generate_schedule_model(config, [], tmp_path)


def test_schedule_and_operation_tracking_generate_in_one_pass(tmp_path: Path):
    source_models = tmp_path / "app/models"
    source_models.mkdir(parents=True)
    (source_models / "employee.py").write_text(
        "from sqlmodel import SQLModel, Field\n"
        "class Employee(SQLModel, table=True):\n"
        "    __onesite__ = {'track': ['crud']}\n"
        "    id: int | None = Field(default=None, primary_key=True)\n"
        "    name: str\n"
    )
    backend = tmp_path / "generated/backend"
    phase_sync_models(tmp_path, backend)
    config = {"schedule": {"enabled": True, "target_model": "Employee", "display_field": "name"}}

    models = phase_introspect(backend, site_config=config, source_path=tmp_path / "app")

    assert {model["name"] for model in models} >= {"Employee", "Schedule", "OperationLog"}
    schedule = next(model for model in models if model["name"] == "Schedule")
    fields = {field["name"]: field for field in schedule["fields"]}
    overrides = {entry["field"]: entry for entry in schedule["override_fields"]}
    assert overrides["weekdays"]["read_type"] == "List[str]"
    assert overrides["month_days"]["read_type"] == "List[str]"
    assert fields["weekdays"]["type"] == "List[int]"
    assert fields["month_days"]["type"] == "List[int]"
    assert fields["weekdays"]["visible_when"] == {"recurrence": ["weekly"]}
    assert fields["month_days"]["visible_when"] == {"recurrence": ["monthly"]}
    assert fields["dates"]["visible_when"] == {"recurrence": ["dates"]}
    assert (backend / "app/models/schedule.py").exists()
    assert (source_models / "schedule.py").read_bytes() == (backend / "app/models/schedule.py").read_bytes()
    assert (backend / "app/models/operation_log.py").exists()

    # Verify the rendered forms: enum lists must never fall through to Select.
    for theme in ("normal", "industrial", "neuron"):
        env = create_template_environment(theme)
        for template in ("frontend_page_create.tsx.j2", "frontend_page_detail.tsx.j2"):
            rendered = env.get_template(template).render(model=schedule, models=models)
            for field_name in ("weekdays", "month_days"):
                controls = re.findall(
                    rf'<Controller\b(?:(?!<Controller).)*?name="{field_name}".*?(?=</div>)',
                    rendered, re.DOTALL,
                )
                assert controls, (theme, template, field_name)
                for control in controls:
                    assert "<SearchableSelect" in control
                    assert "multiple" in control
                    assert "valueLabels=" in control
                    assert "<Select " not in control
                    assert "weekday: 'long'" in control if field_name == "weekdays" else "}日`" in control


def test_existing_schedule_source_is_synced_without_replacement(tmp_path: Path):
    source_models = tmp_path / "app/models"
    source_models.mkdir(parents=True)
    (source_models / "employee.py").write_text(
        "from sqlmodel import SQLModel, Field\n"
        "class Employee(SQLModel, table=True):\n"
        "    id: int | None = Field(default=None, primary_key=True)\n"
        "    name: str\n"
    )
    custom = (
        "from sqlmodel import SQLModel, Field\n"
        "class Schedule(SQLModel, table=True):\n"
        "    id: int | None = Field(default=None, primary_key=True)\n"
        "    label: str\n"
    )
    (source_models / "schedule.py").write_text(custom)
    backend = tmp_path / "generated/backend"
    phase_sync_models(tmp_path, backend)
    config = {"schedule": {"enabled": True, "target_model": "Employee", "display_field": "name"}}
    models = phase_introspect(backend, site_config=config, source_path=tmp_path / "app")
    assert any(model["name"] == "Schedule" for model in models)
    assert (source_models / "schedule.py").read_text() == custom
    assert (backend / "app/models/schedule.py").read_text() == custom
