"""Typed data structures for the code generation pipeline.

Replaces bare dicts and 27-element tuples with well-defined types
so the data flow through the pipeline is explicit and IDE-friendly.
"""

from dataclasses import dataclass, field
from typing import Any

from pydantic_core import PydanticUndefined


# ── Field-level types ───────────────────────────────────────────────────────


@dataclass
class ForeignKeyInfo:
    """Foreign key relationship metadata.

    Created during introspection (Phase 3) and enriched during
    relationship resolution (Phase 4).
    """

    name: str
    target_model: str
    target_service: str
    target_endpoint: str
    label_field: str
    reverse_display: bool = True
    is_self_referencing: bool = False

    # ── Set during relationship resolution (Phase 4) ────────────────────────
    target_source_module: str | None = None
    target_readable_fields: list[dict] | None = None

    # ── Dict-compatible access for pipeline code & Jinja2 templates ─────────

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        object.__setattr__(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def setdefault(self, key: str, default: Any = None) -> Any:
        if not hasattr(self, key) or getattr(self, key) is None:
            object.__setattr__(self, key, default)
            return default
        return getattr(self, key)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)


@dataclass
class FieldDefinition:
    """Introspected metadata for a single model field."""

    name: str
    type: str
    ui_type: str
    json_kind: str | None = None
    json_model_schema: dict | None = None
    json_item_schema: dict | None = None
    json_item_kind: str | None = None
    json_fixed_keys: list[str] | None = None
    json_lock_keys: bool = False
    py_imports: list[str] = field(default_factory=list)
    permissions: str = "cru"
    role_permissions: dict[str, str] | None = None
    create_optional: bool = False
    update_optional: bool = False
    required: bool = True
    default: Any = None
    default_factory: str | None = None
    is_enum: bool = False
    is_multi_select: bool = False
    enum_values: list = field(default_factory=list)
    enum_translations: dict = field(default_factory=dict)
    is_search_field: bool = False
    fk_info: ForeignKeyInfo | None = None
    allow_download: bool = True
    label_key: str = ""
    translations: dict = field(default_factory=dict)
    is_unique: bool = False
    is_local_storage: bool = False
    group: str | None = None

    # ── Dict-compatible access for Jinja2 templates & pipeline code ─────────

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        object.__setattr__(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def setdefault(self, key: str, default: Any = None) -> Any:
        if not hasattr(self, key) or getattr(self, key) is None:
            object.__setattr__(self, key, default)
            return default
        return getattr(self, key)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)


# ── Model-level types ───────────────────────────────────────────────────────


class ModelDefinition(dict):
    """Canonical model metadata for code generation.

    Behaves as a dict for backward compatibility with Jinja2 templates
    and existing mutation code in the pipeline phases, while also
    supporting attribute access (``model.name``) for new / refactored code.

    Fields are set dynamically during the pipeline:
      Phase 3 — :func:`_build_model_dict` sets introspection fields.
      Phase 4 — relationship resolution enriches with relation metadata.
    """

    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError:
            raise AttributeError(
                f"'{type(self).__name__}' has no field '{key}'"
            ) from None

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value


# ── Return type for get_model_fields() ──────────────────────────────────────


@dataclass
class ModelIntrospectResult:
    """Structured return type for :func:`~onesite.codegen.introspect.get_model_fields`.

    Replaces the previous 27-element tuple with named fields.
    """

    fields: list[FieldDefinition]
    foreign_keys: list[ForeignKeyInfo]
    search_field: str
    unique_search_field: str | None
    is_link_table: bool
    is_singleton: bool
    model_permissions: str
    frontend_only: bool
    model_translations: dict
    refresh_interval: int
    reverse_fk_display: bool
    model_site_props: dict
    actions: dict
    is_notification_table: bool
    union_key: list[str] | None
    importable: bool
    exportable: bool
    import_key: str | None
    role_permissions: dict[str, str]
    role_visible: dict[str, bool]
    owner_field: str | None
    page_edit: bool
    is_timescaledb: bool
    timescaledb_entity_field: str | None
    timescaledb_metric_field: str | None
    timescaledb_model_table: str | None
    property_config: dict | None


# ── Pipeline context ────────────────────────────────────────────────────────


@dataclass
class EventListener:
    """A database event listener method extracted from a model.

    Generated from model methods named ``on_orm_before_<event>`` or
    ``on_orm_after_<event>`` (plus legacy insert aliases) — the method body is extracted and wrapped
    in a ``@event.listens_for`` decorated function.

    If ``is_async`` is True the body is routed to a background task
    handler instead of being inlined in the event listener.
    """

    event_name: str   # e.g. "before_insert", "after_update"
    body: str          # dedented source code of the method body
    is_async: bool = False  # async def → background task handler
    has_session_param: bool = False  # method signature has "session" param
    has_old_param: bool = False  # method signature has "old" param (after_update only)


@dataclass
class PipelineContext:
    """Accumulated state passed through the code generation pipeline phases."""

    cwd: str  # project root directory
    site_config: dict | None = None
    backend_path: str | None = None
    models: list[ModelDefinition] | None = None
    api_models: list[ModelDefinition] | None = None
