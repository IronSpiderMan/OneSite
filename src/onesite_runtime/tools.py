"""Declarative project tools, independent of the generator and web framework."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Protocol

from pydantic import BaseModel

from .execution_types import (
    ExecutionOptions,
    InputFile,
    OutputFile,
    ResultUI,
    Role,
    ToolTranslation,
    input_values,
    validation_values,
)

__all__ = [
    "BaseTool",
    "ToolContext",
    "ExecutionOptions",
    "InputFile",
    "OutputFile",
    "ResultUI",
    "Role",
    "ToolTranslation",
    "input_values",
    "validation_values",
]


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
