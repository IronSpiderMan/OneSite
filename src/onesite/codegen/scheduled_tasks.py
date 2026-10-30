"""Compile class tasks while retaining the established APScheduler contract."""

from typing import Any, Literal

from pydantic import Field

from onesite_runtime.tasks import BaseScheduledTask, CronSchedule, IntervalSchedule, NotifyOptions
from onesite_runtime.execution_types import Role

from .tools import ExecutableMetadata, compile_models, declaration_metadata


class _TaskMetadata(ExecutableMetadata):
    schedule: CronSchedule | IntervalSchedule
    enabled: bool
    overlap: Literal["skip", "queue"]
    manual_permissions: list[Role] = Field(min_length=1)
    notify: NotifyOptions
    defaults: dict[str, Any]


def compile_scheduled_task(task: type[BaseScheduledTask]) -> dict[str, Any]:
    metadata = declaration_metadata(task, _TaskMetadata, namespace="tasks", label="Scheduled task")
    models = compile_models(
        task,
        metadata["result_ui"],
        prefix=f"Scheduled task {task.__name__}",
        allow_uploads=False,
    )
    # The old scheduler's params are descriptor/value pairs. Class tasks keep
    # descriptors in inputs, and persist only explicitly supplied overrides.
    return {
        **metadata,
        **models,
        "params": {},
        "timeout_seconds": metadata["execution"]["timeout_seconds"],
    }
