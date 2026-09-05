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

from pydantic import BaseModel, ConfigDict, Field, model_validator


Role = Literal["user", "admin", "developer"]


class _ConfigModel(BaseModel):
    """Base model that keeps compatible, as-yet-untyped configuration keys."""

    model_config = ConfigDict(extra="allow")


class _StrictConfigModel(BaseModel):
    """Strict base for new declarations that have no legacy keys."""

    model_config = ConfigDict(extra="forbid")


class Theme(str, Enum):
    NORMAL = "normal"
    INDUSTRIAL = "industrial"
    NEURON = "neuron"
    ARCO = "arco"


class ListMode(str, Enum):
    """Layout used by generated model collection pages."""

    LIST = "list"
    GRID = "grid"


class EditMode(str, Enum):
    """Editor presentation used by generated model collection pages.

    The serialized values intentionally retain the established generator
    spellings so typed configuration and legacy dictionary configuration can
    coexist without migration.
    """

    FORM_EDIT = "modal"
    PAGE_EDIT = "page"
    INPLACE_EDIT = "inplace_edit"
    DRAWER_EDIT = "drawer"


class DesktopConfig(_ConfigModel):
    identifier: str | None = None
    version: str | None = None
    api_url: str | None = None
    width: int | None = None
    height: int | None = None


class PublicDashboardConfig(_StrictConfigModel):
    """Opt-in, anonymous read-only access to selected Dashboard charts."""

    enabled: bool = False
    path: str = "/share/dashboard"
    title: str = "Dashboard"
    visualizations: list[str] = Field(default_factory=list)
    # Optional developer-owned component under app/frontend/features.  This
    # lets a customized dashboard render the exact same content when shared.
    component: str | None = None

    @model_validator(mode="after")
    def validate_sharing(self) -> "PublicDashboardConfig":
        if not self.path.startswith("/") or self.path == "/" or "?" in self.path or "#" in self.path:
            raise ValueError("path must be a non-root absolute route path")
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if any(not key for key in self.visualizations):
            raise ValueError("visualizations must contain non-empty keys")
        if len(set(self.visualizations)) != len(self.visualizations):
            raise ValueError("visualizations must not contain duplicate keys")
        if self.enabled and not self.visualizations:
            raise ValueError("an enabled public dashboard must list at least one visualization")
        if self.component is not None and (self.component.startswith("/") or ".." in self.component):
            raise ValueError("component must be a relative path under frontend features")
        return self


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


class NavRoute(_ConfigModel):
    type: Literal["route"] = "route"
    route: str


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
    children: list[NavModel | NavRoute | NavBuiltin]


class CustomFeatureMenu(_StrictConfigModel):
    """Navigation metadata for one custom application page."""

    title: dict[Literal["zh", "en"], str]
    icon: str = "PanelsTopLeft"
    visible: list[Role] | None = None


class CustomPage(_StrictConfigModel):
    """A developer-owned page scaffolded and mounted by OneSite."""

    id: str
    path: str
    component: str | None = None
    layout: Literal["app", "public"] = "app"
    access: list[Role] = Field(
        default_factory=lambda: ["user", "admin", "developer"]
    )
    menu: CustomFeatureMenu | None = None


class CustomOverride(_StrictConfigModel):
    """Replace one stable generated route with a developer-owned page."""

    target: str
    component: str | None = None
    access: list[Role] | None = None


class CustomDashboardWidget(_StrictConfigModel):
    """A developer-owned Dashboard widget scaffolded by OneSite."""

    id: str
    title: dict[Literal["zh", "en"], str]
    component: str | None = None
    span: int | dict[Literal["sm", "md", "lg", "xl", "2xl"], int] = 12
    order: int = 100
    access: list[Role] = Field(
        default_factory=lambda: ["user", "admin", "developer"]
    )
    frame: bool = True


class CustomFeature(_StrictConfigModel):
    """A custom full-stack, frontend-only, or backend-only feature."""

    name: str
    frontend_only: bool = False
    backend_only: bool = False
    pages: list[CustomPage] = Field(default_factory=list)
    overrides: list[CustomOverride] = Field(default_factory=list)
    dashboard_widgets: list[CustomDashboardWidget] = Field(default_factory=list)
    dependencies: dict[str, str] = Field(default_factory=dict)
    dev_dependencies: dict[str, str] = Field(default_factory=dict)
    locales: dict[Literal["zh", "en"], str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_mode(self) -> "CustomFeature":
        if self.frontend_only and self.backend_only:
            raise ValueError("frontend_only and backend_only cannot both be true")
        if self.backend_only and (
            self.pages
            or self.overrides
            or self.dashboard_widgets
            or self.dependencies
            or self.dev_dependencies
            or self.locales
        ):
            raise ValueError(
                "backend_only custom features cannot declare pages, overrides, "
                "dashboard_widgets, frontend dependencies, or locales"
            )
        return self


NavigationItem = NavModel | NavRoute | NavBuiltin | NavGroup


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


class MultiDisplayFieldConfig(_ConfigModel):
    """One model field rendered in the optional multi-item display view."""

    field: str
    renderer: Literal["auto", "image", "gallery", "video", "map", "text"] = "auto"
    span: int = Field(default=4, ge=1, le=4)
    fit: Literal["cover", "contain"] = "contain"
    zoom: int = Field(default=15, ge=1, le=18)


class MultiDisplayConfig(_ConfigModel):
    """A selectable media-oriented companion view for a model collection."""

    enabled: bool = True
    fields: list[str | MultiDisplayFieldConfig] = Field(default_factory=list)
    label_field: str | None = None
    default_view: Literal["list", "multi"] = "list"
    max_selected: int = Field(default=4, ge=1, le=9)
    columns: int = Field(default=2, ge=1, le=4)


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


class TimeSeriesLifecycleConfig(_ConfigModel):
    model_config = ConfigDict(extra="forbid")

    chunk_interval: str | None = None
    compress_after: str | None = None
    retention_after: str | None = None
    continuous_aggregate: bool = False
    bucket_interval: str | None = None
    refresh_start_offset: str | None = None
    refresh_end_offset: str | None = None
    refresh_schedule_interval: str | None = None


class TimeSeriesTableConfig(_ConfigModel):
    model_config = ConfigDict(extra="forbid")

    entity_field: str
    metric_field: str | None = None
    metric_label_field: str | None = None
    metric_data_type_field: str | None = None
    metric_unit_field: str | None = None
    time_field: str | None = None
    latest_table: str | None = None
    lifecycle: TimeSeriesLifecycleConfig | None = None


class DefinitionBindingConfig(_ConfigModel):
    """Bind an entity to a separate model that defines keyed items.

    The target definition model is derived from ``definition_fk``.  When an
    ``instance_config_field`` is supplied, its value model is derived from the
    field's ``dict[str, Model]`` annotation rather than repeated in config.
    """

    model_config = ConfigDict(extra="forbid")

    definition_fk: str
    definitions_field: str
    instance_config_field: str | None = None
    key_policy: Literal["definition", "subset", "free"] = "definition"
    on_definition_change: Literal["reset", "merge", "keep"] = "reset"
    protect_definitions_when_used: bool = True


class DictKeyReferenceConfig(_ConfigModel):
    """Reference a key in a JSON ``dict[str, Model]`` through an FK owner.

    The referenced model is derived from ``owner_fk`` and the JSON value model
    is derived from ``source_field``.  This is an application-level relation;
    the database continues to enforce only the real owner foreign key.
    """

    model_config = ConfigDict(extra="forbid")

    owner_fk: str
    source_field: str
    display_field: str | None = None
    on_source_change: Literal["restrict"] = "restrict"


class ExternalResourceConfig(_ConfigModel):
    provider: str
    resource: str


class NetworkDeviceConfig(_StrictConfigModel):
    """Reachability status derived from a URL stored on a model row."""

    url_field: str
    status_field: str = "online"
    checker: str | None = None
    timeout: float = Field(default=1.0, ge=0.05, le=30.0)
    show_in_list: bool = True
    show_in_detail: bool = True
    label: str | dict[str, str] = Field(
        default_factory=lambda: {"en": "Online status", "zh": "在线状态"}
    )
    udp_payload: str = ""


class TreeLeafConfig(_ConfigModel):
    """A related model rendered as terminal records in a tree page."""

    model: str
    parent_field: str | None = None
    label_field: str | None = None
    page_size: int = Field(default=20, ge=1)


class TreeViewConfig(_ConfigModel):
    """Typed configuration for a self-referencing model tree."""

    leaf: str | TreeLeafConfig | None = None


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
    edit_mode: EditMode | None = None
    list_mode: ListMode = ListMode.LIST
    multi_display: MultiDisplayConfig | None = None
    refresh_interval: int = 0
    reverse_fk_display: bool = True
    actions: dict[str, ModelAction] = Field(default_factory=dict)
    ui: ModelUIConfig | None = None
    importable: bool | ImportExportConfig = False
    exportable: bool | ImportExportConfig = False
    import_key: str | None = None
    union_key: list[str] | None = None
    time_series_table: TimeSeriesTableConfig | None = None
    definition_binding: DefinitionBindingConfig | None = None
    dict_key_references: dict[str, DictKeyReferenceConfig] = Field(
        default_factory=dict
    )
    external_resource: ExternalResourceConfig | None = None
    network_device: str | NetworkDeviceConfig | None = None
    tree_view: Literal["auto"] | bool | TreeViewConfig = "auto"
    m2m: dict[str, Any] = Field(default_factory=dict)
    special_me_permissions: ModelPermissions | None = None
    # Deprecated visualization configuration stays typed at the container
    # level while its detailed schema lives in the visualization module.
    visualize: dict[str, Any] | list[dict[str, Any]] | None = None
    dashboard_metrics: list[Any] = Field(default_factory=list)
    reports: ReportsConfig | bool = False
    # Compact CRUD strings (for example ``"rud"``) keep the common case
    # terse. Extended operations use the list form alongside the ``crud``
    # shorthand.
    track: str | list[
        Literal["crud", "c", "r", "u", "d", "bulk_delete", "import", "export"]
    ] | None = None


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


class AgentConfig(_StrictConfigModel):
    """A small built-in agent using an OpenAI-compatible chat endpoint."""

    title: str = "Assistant"
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "AGENT_API_KEY"
    model: str
    instructions: str = "Help the user work with their data."
    roles: list[Role] = Field(default_factory=lambda: ["admin", "developer"])
    max_steps: int = Field(default=20, ge=1, le=100)
    timeout_seconds: int = Field(default=120, ge=1, le=3600)
    model_tools: dict[str, list[str]] = Field(default_factory=dict)
    custom_tools: list[str] = Field(default_factory=list)
    hooks: dict[str, str] = Field(default_factory=dict)


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
    custom_features: list[CustomFeature] = Field(default_factory=list)
    plugins: list[str] = Field(default_factory=list)
    redis: RedisConfig | None = None
    rabbitmq: RabbitMQConfig | None = None
    mqtt: MqttConfig | None = None
    kafka: KafkaConfig | None = None
    video_stream: VideoStreamConfig | None = None
    providers: dict[str, ExternalResourceProviderConfig] = Field(default_factory=dict)
    agents: dict[str, AgentConfig] = Field(default_factory=dict)
    tools: list[DashboardTool] = Field(default_factory=list)
    scheduled_tasks: list[ScheduledTask] = Field(default_factory=list)
    task_center: TaskCenterConfig = Field(default_factory=TaskCenterConfig)
    public_dashboard: PublicDashboardConfig = Field(default_factory=PublicDashboardConfig)


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
