"""Typed, editor-friendly configuration objects for OneSite projects.

Project configuration lives in ``site_config.py`` and exports a ``config``
instance.  The generator converts these models to its stable dictionary
representation before rendering templates, so configuration remains
declarative even though it is authored in Python.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


Role = Literal["user", "admin", "developer"]


class _ConfigModel(BaseModel):
    """Base model that keeps compatible, as-yet-untyped configuration keys."""

    model_config = ConfigDict(extra="allow")


class Theme(str, Enum):
    NORMAL = "normal"
    INDUSTRIAL = "industrial"
    NEURON = "neuron"


class DesktopConfig(_ConfigModel):
    identifier: str | None = None
    version: str | None = None
    api_url: str | None = None
    width: int | None = None
    height: int | None = None


class RedisConfig(_ConfigModel):
    url: str = "redis://localhost:6379/0"
    password: str | None = None


class RabbitMQConfig(_ConfigModel):
    url: str = "amqp://guest:guest@localhost:5672/"


class MqttCallback(_ConfigModel):
    topic: str
    handler: str
    qos: Literal[0, 1, 2] = 1


class MqttConfig(_ConfigModel):
    url: str = "mqtt://localhost:1883"
    username: str | None = None
    password: str | None = None
    client_id: str | None = None
    callbacks: list[MqttCallback] = Field(default_factory=list)


class KafkaCallback(_ConfigModel):
    topic: str
    handler: str
    group_id: str = "onesite_backend"


class KafkaConfig(_ConfigModel):
    brokers: list[str] = Field(default_factory=lambda: ["localhost:9092"])
    callbacks: list[KafkaCallback] = Field(default_factory=list)


class RTSPConfig(_ConfigModel):
    enabled: bool = False
    allowed_hosts: list[str] = Field(default_factory=list)
    connect_timeout_seconds: float = 10
    media_api_url: str = "http://127.0.0.1:9997"
    hls_public_prefix: str = "/media-hls"


class VideoStreamConfig(_ConfigModel):
    rtsp: RTSPConfig = Field(default_factory=RTSPConfig)


class ExternalResourceProviderConfig(_ConfigModel):
    """Location of a developer-owned external-resource provider module."""

    module: str | None = None


class NavModel(_ConfigModel):
    type: Literal["model"] = "model"
    model: str


class NavBuiltin(_ConfigModel):
    type: Literal["builtin"] = "builtin"
    key: Literal["dashboard", "reports", "external-resources"]

    @classmethod
    def dashboard(cls) -> "NavBuiltin":
        return cls(key="dashboard")

    @classmethod
    def reports(cls) -> "NavBuiltin":
        return cls(key="reports")

    @classmethod
    def external_resources(cls) -> "NavBuiltin":
        return cls(key="external-resources")


class NavGroup(_ConfigModel):
    type: Literal["group"] = "group"
    key: str
    label: dict[Literal["zh", "en"], str]
    icon: str = "Folder"
    default_open: bool = False
    visible: list[Role] | dict[Role, bool] | None = None
    children: list[NavModel | NavBuiltin]


NavigationItem = NavModel | NavBuiltin | NavGroup


class ToolExecution(_ConfigModel):
    mode: Literal["background"] = "background"
    timeout_seconds: int = 600


class ToolInput(_ConfigModel):
    name: str
    type: Literal[
        "str", "string", "text", "number", "bool", "boolean", "select",
        "multi_select", "list", "date", "datetime", "file", "files", "json",
    ]
    label: str | None = None
    required: bool = False
    number_kind: Literal["int", "float"] | None = None
    options: list[Any] | None = None
    default: Any = None
    min: float | int | None = None
    max: float | int | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    accept: list[str] | None = None
    max_size_mb: float | None = None
    max_files: int | None = None


class ToolResult(_ConfigModel):
    type: Literal["json", "text", "file", "toast"] = "json"


class DashboardTool(_ConfigModel):
    name: str
    handler: str | None = None
    title: str | None = None
    description: str = ""
    placement: Literal["dashboard"] = "dashboard"
    permissions: list[Role] = Field(default_factory=lambda: ["admin", "developer"])
    execution: ToolExecution = Field(default_factory=ToolExecution)
    inputs: list[ToolInput] = Field(default_factory=list)
    result: ToolResult = Field(default_factory=ToolResult)


class CronSchedule(_ConfigModel):
    type: Literal["cron"] = "cron"
    cron: str


class IntervalSchedule(_ConfigModel):
    type: Literal["interval"] = "interval"
    seconds: int


class ScheduledTaskParam(_ConfigModel):
    type: Literal["str", "string", "text", "select", "number", "bool", "boolean", "multi_select", "list", "json"]
    default: Any = None
    label: str | None = None


class ScheduledTask(_ConfigModel):
    name: str
    handler: str | None = None
    title: str | None = None
    description: str = ""
    enabled: bool = True
    schedule: CronSchedule | IntervalSchedule
    timeout_seconds: int = 600
    overlap: Literal["skip", "queue"] = "skip"
    manual_permissions: list[Role] = Field(default_factory=lambda: ["admin", "developer"])
    notify: dict[str, Any] = Field(
        default_factory=lambda: {"on_success": False, "on_failure": True, "roles": ["developer"]}
    )
    params: dict[str, ScheduledTaskParam] = Field(default_factory=dict)


class SiteConfig(_ConfigModel):
    """The root configuration object exported by a project's ``site_config.py``."""

    project_name: str = "MyApp"
    database_url: str = "sqlite:///./app.db"
    upload_dir: str = "uploads"
    secret_key: str = "changeme"
    access_token_expire_minutes: int = 11520
    first_superuser: str | None = None
    first_superuser_password: str | None = None
    api_url: str | None = None
    logo: str = ""
    logo_link: str = "/dashboard"
    style: Theme | str = Theme.NORMAL
    theme: Theme | str | None = None
    radius: float | None = None
    extra: dict[str, Any] = Field(default_factory=lambda: {"TIMEZONE": "Asia/Shanghai"})
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    )
    desktop: DesktopConfig = Field(default_factory=DesktopConfig)
    navigation: list[NavigationItem] | None = None
    plugins: list[str] = Field(default_factory=list)
    redis: RedisConfig | None = None
    rabbitmq: RabbitMQConfig | None = None
    mqtt: MqttConfig | None = None
    kafka: KafkaConfig | None = None
    video_stream: VideoStreamConfig | None = None
    external_resources: bool = False
    providers: dict[str, ExternalResourceProviderConfig] = Field(default_factory=dict)
    tools: list[DashboardTool] = Field(default_factory=list)
    scheduled_tasks: list[ScheduledTask] = Field(default_factory=list)


_MISSING = object()


def env(name: str, *, default: str | object = _MISSING) -> str:
    """Return an environment value, or raise a useful error when it is required."""

    value = os.environ.get(name)
    if value is not None:
        return value
    if default is not _MISSING:
        return str(default)
    raise RuntimeError(f"Required environment variable {name!r} is not set.")


def sqlite_url(path: str = "app.db") -> str:
    """Build a SQLite URL relative to the generated backend working directory."""

    return f"sqlite:///./{path.lstrip('./')}"
