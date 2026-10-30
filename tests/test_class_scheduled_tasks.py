"""Typed tasks retain APScheduler triggers, persistence and background execution."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from onesite.codegen.config import (
    SiteConfigError,
    load_site_config,
    validate_scheduled_tasks_config,
)
from onesite.codegen.i18n import generate_locale_files
from onesite.generator import generate_code

ROOT = Path(__file__).resolve().parents[1]
SOURCE = """from datetime import date
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, model_validator
from onesite_runtime.tasks import BaseScheduledTask, IntervalSchedule, CronSchedule, NotifyOptions, OutputFile, ResultUI, ScheduledTaskContext

class Row(BaseModel):
    __i18n__ = {'zh': {'fields': {'name': '名称'}}}
    name: str

class Inputs(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    __i18n__ = {'zh': {'fields': {'limit': '条数', 'flag': '启用标记'}}}
    limit: int = Field(default=2, ge=0, le=100)
    flag: bool = False
    optional: int | None = None
    mode: Literal[0, 1] = 0
    day: date = date(2026, 10, 30)
    token: str = Field(default_factory=lambda: str(uuid4()))
    secret: str = Field(default='hidden', validation_alias='credential', exclude=True)
    rows: list[Row] = Field(default_factory=list)

    @model_validator(mode='after')
    def count_rows(self):
        if self.rows and self.limit > len(self.rows):
            raise ValueError('limit exceeds rows')
        return self

class Result(BaseModel):
    __i18n__ = {'zh': {'fields': {'count': '数量', 'report': '报告'}}}
    count: int
    flag: bool
    optional: int | None
    token: str
    day: date
    rows: list[Row]
    invocations: int = Field(le=1)
    user_id: int | None
    trigger: str
    report: OutputFile
    secret_seen: bool

class ReportTask(BaseScheduledTask):
    name = 'report'
    title = 'Report'
    description = 'Create a report'
    inputs = Inputs
    result = Result
    defaults = {'limit': 3}
    schedule = IntervalSchedule(seconds=60)
    notify = NotifyOptions(on_failure=False)
    result_ui = ResultUI(renderer='download', field='report')
    translations = {'zh': {'title': '生成报告', 'description': '生成定期报告'}}

    def __init__(self):
        self.invocations = 0

    async def run(self, inputs: Inputs, context: ScheduledTaskContext) -> Result:
        self.invocations += 1
        await context.set_progress(50, 'Building')
        path = context.output_path('report.txt')
        path.write_text(str(inputs.limit))
        return Result(count=inputs.limit, flag=inputs.flag, optional=inputs.optional,
                      token=inputs.token, day=inputs.day, rows=inputs.rows,
                      invocations=self.invocations, user_id=context.current_user.id if context.current_user else None,
                      trigger=context.trigger, report=context.output_file(path), secret_seen=bool(inputs.secret))

class QueuedTask(ReportTask):
    name = 'queued'
    title = 'Queued'
    overlap = 'queue'

class BadResultTask(ReportTask):
    name = 'bad_result'
    title = 'Bad result'
    async def run(self, inputs, context):
        return {'count': 'invalid'}

class RequiredInputs(BaseModel):
    value: str

class NeedsParamsTask(ReportTask):
    name = 'needs_params'
    title = 'Needs params'
    inputs = RequiredInputs
    defaults = {}
    enabled = False

class MissingParamsTask(NeedsParamsTask):
    name = 'missing_params'
    title = 'Missing params'
    enabled = True
"""
DECLARATIONS = "ReportTask, QueuedTask, BadResultTask, NeedsParamsTask, MissingParamsTask"


def project(root: Path, source: str = SOURCE) -> Path:
    tasks = root / "app/tasks"
    tasks.mkdir(parents=True)
    (root / "app/__init__.py").write_text("")
    (tasks / "__init__.py").write_text("")
    (tasks / "reports.py").write_text(source)
    (tasks / "legacy.py").write_text(
        "async def legacy(*, region, context):\n    return {'region': region}\n"
    )
    (root / "site_config.py").write_text(
        "from onesite.config import SiteConfig, ScheduledTask, IntervalSchedule\n"
        f"from app.tasks.reports import {DECLARATIONS}\n"
        "config = SiteConfig(style='industrial', scheduled_tasks=["
        f"{DECLARATIONS}, ScheduledTask(name='legacy', schedule=IntervalSchedule(seconds=300), "
        "params={'region': {'type': 'str', 'default': 'cn'}})])\n"
    )
    return root


def test_task_classes_compile_and_generate_translations(tmp_path):
    config = load_site_config(project(tmp_path))
    validate_scheduled_tasks_config(config)
    task = config["scheduled_tasks"][0]
    assert task["class_path"] == "app.tasks.reports:ReportTask"
    assert task["interval"] == 60
    assert task["timeout_seconds"] == 600
    assert task["params"] == {}
    assert task["defaults"] == {"limit": 3}
    token = next(field for field in task["inputs"] if field["name"] == "token")
    assert "default" not in token
    generate_locale_files([], tmp_path / "locales", scheduled_tasks=config["scheduled_tasks"])
    zh = json.loads((tmp_path / "locales/zh.json").read_text())["scheduled_task_definitions"][
        "report"
    ]
    assert zh["title"] == "生成报告"
    assert zh["inputs"]["limit"]["label"] == "条数"
    assert zh["inputs"]["rows"]["item"]["fields"]["name"]["label"] == "名称"
    assert zh["result"]["report"]["label"] == "报告"


def test_sync_never_calls_dynamic_defaults(tmp_path):
    source = SOURCE.replace(
        "lambda: str(uuid4())", "lambda: (_ for _ in ()).throw(RuntimeError('factory called'))"
    )
    load_site_config(project(tmp_path, source))


@pytest.mark.parametrize(
    ("before", "after", "message"),
    [
        ("IntervalSchedule(seconds=60)", "IntervalSchedule(seconds=0)", "greater than"),
        ("title = 'Report'", "title = ' '", "title"),
        ("overlap = 'queue'", "overlap = 'replace'", "overlap"),
        (
            "class ReportTask(BaseScheduledTask):",
            "class ReportTask(BaseScheduledTask):\n    manual_permissions = ('owner',)",
            "manual_permissions",
        ),
        ("inputs = Inputs", "inputs = str", "Pydantic"),
    ],
)
def test_invalid_class_tasks_are_rejected(tmp_path, before, after, message):
    with pytest.raises(SiteConfigError, match=message):
        load_site_config(project(tmp_path, SOURCE.replace(before, after)))


def test_scheduled_tasks_reject_transient_upload_inputs(tmp_path):
    source = SOURCE.replace(
        "class Row(BaseModel):",
        "from onesite_runtime.tools import InputFile\n\nclass Row(BaseModel):",
    )
    source = source.replace(
        "    limit: int = Field(default=2, ge=0, le=100)", "    upload: InputFile"
    )
    with pytest.raises(SiteConfigError, match="durable resource IDs"):
        load_site_config(project(tmp_path, source))


def test_class_tasks_run_with_real_apscheduler_and_recover_snapshots(tmp_path, monkeypatch):
    root = project(tmp_path)
    monkeypatch.chdir(root)
    generate_code()
    backend = root / "generated/backend"
    generated = (backend / "app/tasks/reports.py").read_text()
    assert "onesite_runtime" not in generated
    assert "from app.core.scheduled_task_types import" in generated
    assert not (root / "app/tasks/report.py").exists()
    assert (backend / "app/core/execution_types.py").exists()
    script = (ROOT / "tests/support/class_scheduled_tasks_scenario.py").read_text()
    result = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=backend,
        env={
            **os.environ,
            "PYTHONPATH": "",
            "TASKS_STATE_FILE": str(backend / "test_tasks_state.json"),
        },
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
