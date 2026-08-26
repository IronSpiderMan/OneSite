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
    """One external system that can synchronize multiple resource kinds."""

    module: str | None = None


class NavModel(_ConfigModel):
    type: Literal["model"] = "model"
    model: str


class NavBuiltin(_ConfigModel):
    type: Literal["builtin"] = "builtin"
    key: Literal[
        "dashboard",
        "reports",
        "external-resources",
        "task-center",
    ]

    @classmethod
    def dashboard(cls) -> "NavBuiltin":
        return cls(key="dashboard")

    @classmethod
    def reports(cls) -> "NavBuiltin":
        return cls(key="reports")

    @classmethod
    def external_resources(cls) -> "NavBuiltin":
        return cls(key="external-resources")

    @classmethod
    def task_center(cls) -> "NavBuiltin":
        return cls(key="task-center")


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


class HiddenTask(_ConfigModel):
    """One task kind/name pair omitted from the generated Task Center."""

    kind: Literal["import", "export", "tool", "scheduled_task"]
    name: str


class TaskCenterConfig(_ConfigModel):
    hidden: list[HiddenTask] = Field(default_factory=list)


# ── Model-level ``__onesite__`` configuration ─────────────────────────────


ModelPermissions = str | dict[Role, str]
ModelVisibility = bool | Role | list[Role] | dict[Role, bool]


class ModelAction(_ConfigModel):
    """A custom action rendered on a model's list/detail pages."""

    permissions: str | None = None
    label: str | None = None
    unavailable: Literal["hide", "disable"] | None = None
    toggle: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    condition: Any = None


class ImportExportConfig(_ConfigModel):
    """CSV or custom import/export behavior for a model."""

    custom: bool = False
    fields: list[str] | None = None
    foreign_keys: dict[str, str] = Field(default_factory=dict)
    reverse_foreign_keys: dict[str, str] = Field(default_factory=dict)
    m2m: dict[str, str] = Field(default_factory=dict)


class DetailUIConfig(_ConfigModel):
    # Layout nodes are deliberately open: the recursive layout grammar accepts
    # field names, rows, and nested section objects, and is validated against
    # the actual model fields during introspection.
    layout: list[Any]


class FormUIConfig(_ConfigModel):
    """Editable create/update form layout for a model."""

    layout: list[Any]


class ModelUIConfig(_ConfigModel):
    detail: DetailUIConfig | None = None
    form: FormUIConfig | None = None


class TimeSeriesTableConfig(_ConfigModel):
    entity_field: str
    metric_field: str | None = None
    time_field: str | None = None
    model_table: str | None = None
    property_config: dict[str, Any] | None = None


class ExternalResourceConfig(_ConfigModel):
    provider: str
    resource: str


ReportCategory = Literal[
    "cartesian",
    "multi_cartesian",
    "composition",
    "scatter",
]
ReportBin = Literal[
    "none", "auto", "1m", "5m", "15m", "hour", "day", "week", "month",
]
ReportAggregation = Literal[
    "raw", "sum", "avg", "min", "max", "median", "count", "distinct_count",
]


class ReportDimensionInput(_ConfigModel):
    """A model field that users may bind to a report dimension slot."""

    bins: list[ReportBin] = Field(default_factory=lambda: ["none"])


class ReportMeasureInput(_ConfigModel):
    """A model field that users may bind to a numeric report slot."""

    aggregations: list[ReportAggregation] = Field(default_factory=lambda: ["raw"])


class ReportInputs(_ConfigModel):
    """Field allowlists for the four stable self-service report inputs."""

    x: dict[str, ReportDimensionInput] = Field(default_factory=dict)
    y: dict[str, ReportMeasureInput] = Field(default_factory=dict)
    cls: list[str] = Field(default_factory=list)
    count: list[str] = Field(default_factory=lambda: ["$rows"])


class ReportLimits(_ConfigModel):
    max_rows: int = 5000
    max_series: int = 20
    max_categories: int = 100
    max_span_days: int = 366


class ReportsConfig(_ConfigModel):
    """Self-service reporting capabilities exposed by one model.

    Models enable broad chart categories and field bindings. Concrete chart
    styles remain owned by OneSite and are selected on the generated page.
    """

    enabled: bool = True
    categories: list[ReportCategory]
    inputs: ReportInputs
    filters: list[str] = Field(default_factory=list)
    visible: list[Role] | None = None
    limits: ReportLimits = Field(default_factory=ReportLimits)


class OneSiteConfig(_ConfigModel):
    """Typed, editor-friendly configuration for a model's ``__onesite__``.

    Unknown keys remain supported so new generator features and legacy
    projects can adopt this class without waiting for every option to be
    represented explicitly.
    """

    translations: dict[str, Any] = Field(default_factory=dict)
    icon: str | None = None
    permissions: ModelPermissions | None = None
    visible: ModelVisibility | None = None
    owner_field: str | None = None
    is_link_table: bool = False
    is_singleton: bool = False
    frontend_only: bool = False
    is_notification_table: bool = False
    is_latest_table: bool = False
    standalone: bool = True
    page_edit: bool = False
    edit_mode: Literal["modal", "page", "drawer"] | None = None
    refresh_interval: int = 0
    reverse_fk_display: bool = True
    actions: dict[str, ModelAction] = Field(default_factory=dict)
    ui: ModelUIConfig | None = None
    importable: bool | ImportExportConfig = False
    exportable: bool | ImportExportConfig = False
    import_key: str | None = None
    union_key: list[str] | None = None
    time_series_table: TimeSeriesTableConfig | None = None
    # Legacy flat TimescaleDB spelling, retained for migration compatibility.
    is_timescaledb: bool = False
    timescaledb_entity_field: str | None = None
    timescaledb_metric_field: str | None = None
    timescaledb_time_field: str | None = None
    timescaledb_model_table: str | None = None
    external_resource: ExternalResourceConfig | None = None
    tree_view: Literal["auto"] | bool = "auto"
    m2m: dict[str, Any] = Field(default_factory=dict)
    special_me_permissions: ModelPermissions | None = None
    # Deprecated configurations stay typed at the container level while their
    # detailed schemas continue to live in the visualization/report modules.
    visualize: dict[str, Any] | list[dict[str, Any]] | None = None
    dashboard_metrics: list[Any] = Field(default_factory=list)
    data_reports: list[dict[str, Any]] = Field(default_factory=list)
    reports: ReportsConfig | bool = False


# A discoverable alias for users who search for "model config" in an editor.
ModelConfig = OneSiteConfig


def normalize_onesite_config(value: Any) -> dict[str, Any] | None:
    """Normalize legacy dictionaries and typed ``__onesite__`` values.

    ``exclude_unset`` is important here: an empty :class:`OneSiteConfig`
    behaves like an empty dictionary instead of overriding generator defaults.
    """

    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, OneSiteConfig):
        return value.model_dump(mode="python", exclude_unset=True)
    return None


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
    task_center: TaskCenterConfig = Field(default_factory=TaskCenterConfig)


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
