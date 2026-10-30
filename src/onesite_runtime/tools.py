"""Declarative project tools, usable during generation and at runtime.

This module has no generator, database or web framework dependency. OneSite
copies it into the generated application and rewrites project tool imports.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field
from pydantic_core import to_jsonable_python


Role = Literal["user", "admin", "developer"]


class ExecutionOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["background"] = "background"
    timeout_seconds: int = Field(default=600, gt=0, strict=True)


class ResultUI(BaseModel):
    model_config = ConfigDict(extra="forbid")

    renderer: Literal["detail", "json", "text", "table", "download"] = "detail"
    field: str | None = None


class ToolTranslation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None
    execute_label: str | None = None


class InputFile(BaseModel):
    """A server-saved upload. Paths are assigned by the upload endpoint only."""

    model_config = ConfigDict(extra="forbid")

    path: Path
    name: str
    size: int = Field(ge=0)
    content_type: str | None = None

    def read_bytes(self) -> bytes:
        return self.path.read_bytes()

    def read_text(self, encoding: str = "utf-8") -> str:
        return self.path.read_text(encoding=encoding)


class OutputFile(BaseModel):
    """Public metadata for a file registered through context.output_file()."""

    model_config = ConfigDict(extra="forbid")

    name: str
    download_url: str = Field(pattern=r"^/uploads/tools/[^/]+/outputs/.+")
    size: int = Field(ge=0)
    content_type: str | None = None


class ToolContext(Protocol):
    task_id: str
    user_id: int
    current_user: Any
    session: Any

    @property
    def output_dir(self) -> Path: ...

    def output_path(self, filename: str) -> Path: ...

    def output_file(self, path: str | Path, *, content_type: str | None = None) -> OutputFile: ...

    async def set_progress(self, progress: int, message: str | None = None) -> None: ...

    async def run_sync(self, function: Any, *args: Any, **kwargs: Any) -> Any: ...


class BaseTool(ABC):
    """Subclass in app/tools and explicitly register the class in SiteConfig.

    inputs/result must be Pydantic model classes. All declaration attributes
    are validated by site sync. Instances are created once per execution.
    """

    name: ClassVar[str]
    title: ClassVar[str]
    description: ClassVar[str] = ""
    permissions: ClassVar[tuple[Role, ...] | list[Role]] = ("admin", "developer")
    inputs: ClassVar[type[BaseModel]]
    result: ClassVar[type[BaseModel]]
    execution: ClassVar[ExecutionOptions] = ExecutionOptions()
    result_ui: ClassVar[ResultUI] = ResultUI()
    translations: ClassVar[dict[str, ToolTranslation | dict[str, str]]] = {}

    @abstractmethod
    async def run(self, inputs: Any, context: ToolContext) -> Any:
        """Return data matching the declared result model."""


def validation_values(value: Any) -> Any:
    """Extract validation data recursively, retaining extras and excluded fields."""
    if isinstance(value, BaseModel):
        return {
            **{key: validation_values(item) for key, item in (value.model_extra or {}).items()},
            **{
                field.validation_alias or field.alias or name: validation_values(
                    getattr(value, name)
                )
                for name, field in type(value).model_fields.items()
            },
        }
    if isinstance(value, dict):
        return {key: validation_values(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return type(value)(validation_values(item) for item in value)
    return value


def input_values(value: BaseModel) -> dict[str, Any]:
    """Snapshot queue inputs using validation aliases and JSON scalar types.

    Public execution history is serialized separately using normal model
    exclusion/serialization rules.
    """
    return to_jsonable_python(validation_values(value))
