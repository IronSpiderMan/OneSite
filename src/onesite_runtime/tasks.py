"""Typed scheduled tasks; scheduling remains the application's APScheduler job."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .execution_types import ExecutionOptions, OutputFile, ResultUI, Role, ToolTranslation

__all__ = [
    "BaseScheduledTask",
    "ScheduledTaskContext",
    "CronSchedule",
    "IntervalSchedule",
    "NotifyOptions",
    "ExecutionOptions",
    "OutputFile",
    "ResultUI",
    "Role",
    "ToolTranslation",
]


class CronSchedule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["cron"] = "cron"
    cron: str


class IntervalSchedule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["interval"] = "interval"
    seconds: int = Field(gt=0, strict=True)


class NotifyOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    on_success: bool = False
    on_failure: bool = True
    roles: list[Role] = Field(default_factory=lambda: ["developer"])


class ScheduledTaskContext(Protocol):
    execution_id: str
    trigger: str
    requested_by: int | None
    current_user: Any | None
    session: Any

    @property
    def output_dir(self) -> Path: ...

    def output_path(self, filename: str) -> Path: ...

    def output_file(self, path: str | Path, *, content_type: str | None = None) -> OutputFile: ...

    async def set_progress(self, progress: int, message: str | None = None) -> None: ...

    async def run_sync(self, function: Any, *args: Any, **kwargs: Any) -> Any: ...


class BaseScheduledTask(ABC):
    """Declare in app/tasks and register the class in SiteConfig.scheduled_tasks."""

    name: ClassVar[str]
    title: ClassVar[str]
    description: ClassVar[str] = ""
    inputs: ClassVar[type[BaseModel]]
    result: ClassVar[type[BaseModel]]
    schedule: ClassVar[CronSchedule | IntervalSchedule]
    enabled: ClassVar[bool] = True
    overlap: ClassVar[Literal["skip", "queue"]] = "skip"
    manual_permissions: ClassVar[tuple[Role, ...] | list[Role]] = ("admin", "developer")
    execution: ClassVar[ExecutionOptions] = ExecutionOptions()
    notify: ClassVar[NotifyOptions] = NotifyOptions()
    result_ui: ClassVar[ResultUI] = ResultUI()
    translations: ClassVar[dict[str, ToolTranslation | dict[str, str]]] = {}
    defaults: ClassVar[dict[str, Any]] = {}

    @abstractmethod
    async def run(self, inputs: Any, context: ScheduledTaskContext) -> Any:
        """Return data matching result; automatic executions have no current_user."""
