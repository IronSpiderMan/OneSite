"""Class tool contracts and execution in independently generated applications."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from onesite.codegen.config import SiteConfigError, load_site_config, validate_tools_config
from onesite.codegen.i18n import generate_locale_files
from onesite.generator import generate_code
from onesite_runtime.tools import input_values, validation_values


ROOT = Path(__file__).resolve().parents[1]
SOURCE = """from datetime import date
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator
from onesite_runtime.tools import BaseTool, InputFile, OutputFile, ResultUI, ToolContext

class Row(BaseModel):
    __i18n__ = {'zh': {'fields': {'name': '名称'}}}
    name: str

class Inputs(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    __i18n__ = {'zh': {'fields': {'text': {'title': '原文', 'help': '待处理的文本'}, 'mode': '模式'}, 'enums': {'mode': {0: '大写', 1: '小写'}}}}
    text: str = Field(min_length=1, json_schema_extra={'site_props': {'component': 'textarea'}})
    count: int = Field(default=0, ge=0)
    flag: bool = False
    optional: int | None = None
    mode: Literal[0, 1] = 0
    token: str = Field(default_factory=lambda: str(uuid4()))
    day: date = date(2026, 10, 30)
    rows: list[Row] = Field(default_factory=list)

    @field_validator('text')
    @classmethod
    def reject_bad(cls, value):
        if value == 'bad':
            raise ValueError('bad text is forbidden')
        return value

    @model_validator(mode='after')
    def check_count(self):
        if self.count > len(self.text):
            raise ValueError('count exceeds text length')
        return self

class Result(BaseModel):
    __i18n__ = {'zh': {'fields': {'content': '处理结果'}}}
    content: str
    count: int
    flag: bool
    optional: int | None
    token: str
    day: date
    invocations: int = Field(le=1)
    rows: list[Row]

class Transform(BaseTool):
    name = 'transform'
    title = 'Transform'
    inputs = Inputs
    result = Result
    translations = {'zh': {'title': '文本转换', 'description': '转换文本', 'execute_label': '开始转换'}}

    def __init__(self):
        self.invocations = 0

    async def run(self, inputs: Inputs, context: ToolContext) -> Result:
        self.invocations += 1
        await context.set_progress(50, 'Halfway')
        return Result(content=inputs.text.upper() if inputs.mode == 0 else inputs.text.lower(), count=inputs.count,
                      flag=inputs.flag, optional=inputs.optional, token=inputs.token, day=inputs.day,
                      invocations=self.invocations, rows=inputs.rows)

class BadResult(Transform):
    name = 'bad_result'
    title = 'Bad result'
    async def run(self, inputs, context):
        return {'content': 'missing fields'}

class FileInputs(BaseModel):
    upload: InputFile = Field(json_schema_extra={'site_props': {'accept': ['.txt'], 'max_size_mb': 0.001}})
    others: list[InputFile] = Field(default_factory=list, max_length=2, json_schema_extra={'site_props': {'accept': ['.txt']}})

class FileResult(BaseModel):
    report: OutputFile
    size: int

class FileTool(BaseTool):
    name = 'merge_files'
    title = 'Merge files'
    inputs = FileInputs
    result = FileResult
    result_ui = ResultUI(renderer='download', field='report')
    async def run(self, inputs, context):
        path = context.output_path('merged.txt')
        path.write_bytes(inputs.upload.read_bytes() + b''.join(item.read_bytes() for item in inputs.others))
        return FileResult(report=context.output_file(path, content_type='text/plain'), size=path.stat().st_size)

class AliasedInputs(BaseModel):
    text: str = Field(validation_alias='incoming', serialization_alias='private', exclude=True)

class AliasedResult(BaseModel):
    content: str = Field(validation_alias='value', serialization_alias='rendered')

    @computed_field
    @property
    def length(self) -> int:
        return len(self.content)

class AliasedTool(BaseTool):
    name = 'aliased'
    title = 'Aliased'
    inputs = AliasedInputs
    result = AliasedResult
    async def run(self, inputs, context):
        return AliasedResult(value=inputs.text)
"""


def project(
    root: Path,
    *,
    source: str = SOURCE,
    declarations: str = "Transform, BadResult, FileTool, AliasedTool",
) -> Path:
    tools = root / "app" / "tools"
    tools.mkdir(parents=True)
    (root / "app" / "__init__.py").write_text("")
    (tools / "__init__.py").write_text("")
    (tools / "demo.py").write_text(source)
    (root / "site_config.py").write_text(
        "from onesite.config import SiteConfig\n"
        f"from app.tools.demo import {declarations}\n"
        f"config = SiteConfig(tools=[{declarations}])\n"
    )
    return root


def test_class_tools_compile_constraints_and_locales_without_calling_factories(tmp_path):
    root = project(tmp_path)
    config = load_site_config(root)
    validate_tools_config(config)
    tool = config["tools"][0]
    assert tool["class_path"] == "app.tools.demo:Transform"
    fields = {item["name"]: item for item in tool["inputs"]}
    assert fields["text"]["type"] == "text"
    assert fields["text"]["required"] is True
    assert fields["text"]["min_length"] == 1
    assert fields["mode"]["options"] == [0, 1]
    assert fields["optional"]["nullable"] is True
    assert "default" not in fields["token"]
    assert "default" not in fields["rows"]
    assert fields["count"]["default"] == 0
    generate_locale_files([], root / "locales", tools=config["tools"])
    zh = json.loads((root / "locales/zh.json").read_text())["tool_definitions"]["transform"]
    assert zh["title"] == "文本转换"
    assert zh["inputs"]["text"]["label"] == "原文"
    assert zh["inputs"]["mode"]["options"]["0"] == "大写"
    assert zh["inputs"]["rows"]["item"]["fields"]["name"]["label"] == "名称"
    assert zh["result"]["content"]["label"] == "处理结果"


def test_factories_are_not_evaluated_at_sync(tmp_path):
    source = SOURCE.replace(
        "lambda: str(uuid4())", "lambda: (_ for _ in ()).throw(RuntimeError('factory called'))"
    )
    load_site_config(project(tmp_path, source=source))


def test_nullable_fields_keep_explicit_titles(tmp_path):
    source = SOURCE.replace(
        "optional: int | None = None",
        "optional: int | None = Field(default=None, title='Nullable count')",
    )
    tool = load_site_config(project(tmp_path, source=source))["tools"][0]
    field = next(item for item in tool["inputs"] if item["name"] == "optional")
    assert field["label"] == "Nullable count"
    assert field["default"] is None


def test_root_models_fail_during_sync(tmp_path):
    source = SOURCE.replace(
        "from pydantic import BaseModel,", "from pydantic import RootModel, BaseModel,"
    )
    source = source.replace(
        "class Transform(BaseTool):",
        "class Empty(RootModel[dict]):\n    pass\n\nclass Transform(BaseTool):",
    )
    source = source.replace("inputs = Inputs", "inputs = Empty")
    with pytest.raises(SiteConfigError, match="RootModel"):
        load_site_config(project(tmp_path, source=source))


def test_config_imports_are_isolated_and_reloaded(tmp_path):
    first = project(tmp_path / "first")
    second = project(
        tmp_path / "second",
        source=SOURCE.replace("title = 'Transform'", "title = 'Second project'"),
    )
    assert load_site_config(first)["tools"][0]["title"] == "Transform"
    assert load_site_config(second)["tools"][0]["title"] == "Second project"
    assert load_site_config(first)["tools"][0]["title"] == "Transform"


@pytest.mark.parametrize(
    ("before", "after", "message"),
    [
        ("title = 'Transform'", "title = ' '", "title"),
        ("name = 'transform'", "name = 'bad-name'", "identifier"),
        (
            "class Transform(BaseTool):",
            "class Transform(BaseTool):\n    permissions = ('owner',)",
            "permissions",
        ),
        (
            "async def run(self, inputs: Inputs, context: ToolContext)",
            "def run(self, inputs: Inputs, context: ToolContext)",
            "must be async",
        ),
        ("inputs = Inputs", "inputs = str", "Pydantic"),
        ("text: str = Field(min_length=1,", "text: str | int = Field(", "nullable unions"),
    ],
)
def test_invalid_class_declarations_fail_with_context(tmp_path, before, after, message):
    source = SOURCE.replace(before, after)
    if message == "must be async":
        source = source.replace("await context.set_progress", "context.set_progress")
    root = project(tmp_path, source=source)
    with pytest.raises(SiteConfigError, match=message):
        load_site_config(root)


def test_nested_file_paths_cannot_be_supplied_as_json(tmp_path):
    source = SOURCE.replace("name: str\n", "name: str\n    attachment: InputFile\n")
    with pytest.raises(SiteConfigError, match="top-level InputFile"):
        load_site_config(project(tmp_path, source=source))


def test_queue_snapshots_keep_extras_aliases_and_excluded_fields():
    class Inputs(BaseModel):
        model_config = ConfigDict(extra="allow")
        secret: str = Field(
            validation_alias="incoming", serialization_alias="outgoing", exclude=True
        )

    value = Inputs.model_validate({"incoming": "secret", "extra": False})
    assert input_values(value) == {"incoming": "secret", "extra": False}
    assert value.model_dump(mode="json") == {"extra": False}


def test_nested_result_instances_are_revalidated():
    class Child(BaseModel):
        count: int = Field(ge=0)

    class Result(BaseModel):
        rows: list[Child]

    result = Result(rows=[Child(count=1)])
    result.rows[0].count = -1
    with pytest.raises(ValidationError, match="greater than or equal"):
        Result.model_validate(validation_values(result))


def test_legacy_tools_can_be_mixed_with_classes(tmp_path, monkeypatch):
    root = project(tmp_path)
    config_path = root / "site_config.py"
    config_path.write_text(
        config_path.read_text()
        .replace(
            "SiteConfig\n",
            "SiteConfig, Tool, ToolInput\n",
        )
        .replace(
            "tools=[", "tools=[Tool(name='legacy', inputs=[ToolInput(name='text', type='str')]), "
        )
    )
    monkeypatch.chdir(root)
    generate_code()
    assert (root / "app/tools/legacy.py").exists()
    registry = (root / "generated/backend/app/core/tool_registry.py").read_text()
    assert '"legacy": legacy' in registry
    assert '"transform": _tool_' in registry


def test_generated_class_tools_execute_without_onesite(tmp_path, monkeypatch):
    root = project(tmp_path)
    monkeypatch.chdir(root)
    generate_code()
    backend = root / "generated" / "backend"
    source = (backend / "app/tools/demo.py").read_text()
    assert "onesite_runtime" not in source
    assert "from app.core.tool_types import" in source
    assert not (root / "app/tools/transform.py").exists()
    script = (ROOT / "tests/support/class_tools_scenario.py").read_text()
    result = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=backend,
        env={**os.environ, "PYTHONPATH": ""},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
