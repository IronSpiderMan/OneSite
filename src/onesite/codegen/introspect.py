"""Inspect SQLModel tables and assemble metadata for code generation.

Domain-specific normalization lives in ``metadata``. Existing helper imports
remain available here for compatibility with integrations and older callers.
"""

import inspect
from datetime import date as date_type, datetime as datetime_type, time as time_type
from typing import Any, Dict, List, get_args, get_origin

from pydantic_core import PydanticUndefined
from rich.console import Console
from sqlmodel import SQLModel

from onesite.config import normalize_onesite_config

from .naming import to_snake as _to_snake
from .types import FieldDefinition, ForeignKeyInfo, ModelIntrospectResult
from .metadata.fields import (
    _is_pydantic_model as _is_pydantic_model,
    _unwrap_optional as _unwrap_optional,
    _get_numeric_bounds as _get_numeric_bounds,
    _get_field_site_props as _get_field_site_props,
)
from .metadata.json_schema import (
    _json_field_kind_from_annotation as _json_field_kind_from_annotation,
    _normalize_json_condition as _normalize_json_condition,
    _get_json_model_ui as _get_json_model_ui,
    _get_json_model_i18n as _get_json_model_i18n,
    _normalize_json_model_layout as _normalize_json_model_layout,
    _build_json_model_schema as _build_json_model_schema,
    _json_schema_has_conditions as _json_schema_has_conditions,
    _json_schema_root_controllers as _json_schema_root_controllers,
)
from .metadata.permissions import (
    ROLE_ORDER as ROLE_ORDER,
    ROLE_LEVELS as ROLE_LEVELS,
    _parse_model_permissions as _parse_model_permissions,
    _compute_flat_perms as _compute_flat_perms,
    _parse_visible as _parse_visible,
    _parse_field_permissions as _parse_field_permissions,
)
from .metadata.reports import (
    REPORT_CATEGORIES as REPORT_CATEGORIES,
    REPORT_BINS as REPORT_BINS,
    REPORT_AGGREGATIONS as REPORT_AGGREGATIONS,
    REPORT_NUMERIC_TYPES as REPORT_NUMERIC_TYPES,
    REPORT_UNSUPPORTED_TYPES as REPORT_UNSUPPORTED_TYPES,
    _normalize_reports as _normalize_reports,
)
from .metadata.dashboard_metrics import (
    DASHBOARD_METRIC_AGGREGATIONS as DASHBOARD_METRIC_AGGREGATIONS,
    DASHBOARD_METRIC_PERIODS as DASHBOARD_METRIC_PERIODS,
    _normalize_dashboard_metric_calculation as _normalize_dashboard_metric_calculation,
    _normalize_dashboard_metrics as _normalize_dashboard_metrics,
)
from .metadata.tracking import (
    TRACK_CRUD_OPERATIONS as TRACK_CRUD_OPERATIONS,
    TRACK_EXTENDED_OPERATIONS as TRACK_EXTENDED_OPERATIONS,
    _normalize_tracked_operations as _normalize_tracked_operations,
)
from .metadata.display import (
    _normalize_multi_display as _normalize_multi_display,
)

console = Console()


def get_model_fields(
    model_cls: type[SQLModel], module_name: str | None = None
) -> ModelIntrospectResult:
    model_site_props: Dict[str, Any] = {}
    onesite_config = normalize_onesite_config(getattr(model_cls, "__onesite__", None))
    if onesite_config is not None:
        model_site_props.update(onesite_config)
    if hasattr(model_cls, "__site_props__") and isinstance(getattr(model_cls, "__site_props__"), dict):
        model_site_props.update(getattr(model_cls, "__site_props__"))

    if hasattr(model_cls, "__table_args__") and isinstance(model_cls.__table_args__, dict):
        info = model_cls.__table_args__.get("info", {})
        table_site_props = info.get("site_props", {})
        if isinstance(table_site_props, dict):
            model_site_props = {**table_site_props, **model_site_props}

    is_link_table = model_site_props.get("is_link_table", False)
    is_singleton = model_site_props.get("is_singleton", False)
    raw_permissions = model_site_props.get("permissions", "rcud")
    frontend_only = model_site_props.get("frontend_only", False)

    # Built-in model auto-detection — these flags can be omitted from __onesite__
    model_cls_name = getattr(model_cls, "__name__", "")
    if model_cls_name == "SystemConfig" and module_name == "system_config":
        is_singleton = True
    if model_cls_name == "CustomConfig" and module_name == "custom_config":
        frontend_only = True
    model_translations = model_site_props.get("translations", {})
    refresh_interval = model_site_props.get("refresh_interval", 0)
    reverse_fk_display = model_site_props.get("reverse_fk_display", True)
    actions = model_site_props.get("actions", {})
    # Normalize action-level permissions (default: developer + admin).
    # ``toggle`` is a convenience form for the common enable/disable action:
    # {"toggle_enabled": {"toggle": "enabled"}}.
    # It expands to the existing safe boolean inversion expression, so the API
    # and all permission checks keep following the regular action path.
    for action_name, action_config in actions.items():
        if isinstance(action_config, dict):
            action_config.setdefault("permissions", "da")
            toggle_field = action_config.get("toggle")
            if toggle_field is not None:
                if not isinstance(toggle_field, str) or not toggle_field:
                    raise ValueError(
                        f"Invalid toggle action {action_name!r} on {model_cls.__name__}: "
                        "'toggle' must be a non-empty field name."
                    )
                data = action_config.setdefault("data", {})
                if not isinstance(data, dict):
                    raise ValueError(
                        f"Invalid toggle action {action_name!r} on {model_cls.__name__}: "
                        "'data' must be a dictionary."
                    )
                if toggle_field in data and data[toggle_field] != "!{{value}}":
                    raise ValueError(
                        f"Invalid toggle action {action_name!r} on {model_cls.__name__}: "
                        f"do not also set data for toggle field {toggle_field!r}."
                    )
                data[toggle_field] = "!{{value}}"
    is_notification_table = bool(model_site_props.get("is_notification_table", False))
    union_key = model_site_props.get("union_key", None)
    raw_importable = model_site_props.get("importable", False)
    importable = isinstance(raw_importable, dict) or bool(raw_importable)
    import_key = model_site_props.get("import_key", None)
    raw_exportable = model_site_props.get("exportable", False)
    exportable = isinstance(raw_exportable, dict) or bool(raw_exportable)
    tracked_operations = _normalize_tracked_operations(
        model_site_props.get("track"), model_name=model_cls.__name__
    )
    if tracked_operations and frontend_only:
        raise ValueError(
            f"Model '{model_cls.__name__}': frontend-only models cannot enable track"
        )
    if "import" in tracked_operations and not importable:
        raise ValueError(
            f"Model '{model_cls.__name__}': track includes import but importable is disabled"
        )
    if "export" in tracked_operations and not exportable:
        raise ValueError(
            f"Model '{model_cls.__name__}': track includes export but exportable is disabled"
        )
    unsupported_singleton_operations = {
        "create", "delete", "bulk_delete", "import", "export"
    }.intersection(tracked_operations)
    if unsupported_singleton_operations and is_singleton:
        raise ValueError(
            f"Model '{model_cls.__name__}': singleton models only support read/update tracking"
        )
    model_site_props["tracked_operations"] = tracked_operations
    raw_visible = model_site_props.get("visible", None)
    # ``page_edit`` is the legacy boolean spelling.  ``edit_mode`` is the
    # extensible form and supports modal (default), page, right-side drawer,
    # and editing the selected row directly in the paginated table.
    raw_edit_mode = model_site_props.get("edit_mode")
    if raw_edit_mode is None:
        edit_mode = "page" if model_site_props.get("page_edit", False) else "modal"
    elif isinstance(raw_edit_mode, str) and raw_edit_mode in {
        "modal", "page", "drawer", "inplace_edit"
    }:
        edit_mode = raw_edit_mode
    else:
        raise ValueError(
            f"Invalid edit_mode for {model_cls.__name__}: {raw_edit_mode!r}. "
            "Expected 'modal', 'page', 'drawer', or 'inplace_edit'."
        )
    page_edit = edit_mode == "page"
    raw_list_mode = model_site_props.get("list_mode", "list")
    if isinstance(raw_list_mode, str) and raw_list_mode in {"list", "grid"}:
        list_mode = raw_list_mode
    else:
        raise ValueError(
            f"Invalid list_mode for {model_cls.__name__}: {raw_list_mode!r}. "
            "Expected 'list' or 'grid'."
        )
    owner_field = model_site_props.get("owner_field", None)  # FK field name for user-owner filtering

    # ── TimescaleDB / time-series config ──────────────────────────────────
    ts_config = model_site_props.get("time_series_table")
    if ts_config:
        is_timescaledb = True
        timescaledb_entity_field = ts_config.get("entity_field")
        timescaledb_metric_field = ts_config.get("metric_field")
        timescaledb_time_field = ts_config.get("time_field")
    else:
        is_timescaledb = False
        timescaledb_entity_field = None
        timescaledb_metric_field = None
        timescaledb_time_field = None

    removed_timeseries_keys = {
        "is_timescaledb",
        "timescaledb_entity_field",
        "timescaledb_metric_field",
        "timescaledb_time_field",
        "timescaledb_model_table",
    }
    configured_removed_keys = sorted(removed_timeseries_keys.intersection(model_site_props))
    if configured_removed_keys:
        raise ValueError(
            f"Removed TimescaleDB configuration on {model_cls.__name__}: "
            + ", ".join(configured_removed_keys)
            + ". Use time_series_table instead."
        )
    if ts_config:
        removed_nested_keys = sorted({"model_table", "property_config"}.intersection(ts_config))
        if removed_nested_keys:
            raise ValueError(
                f"Removed time_series_table configuration on {model_cls.__name__}: "
                + ", ".join(removed_nested_keys)
                + ". Move definition/config behavior to definition_binding on the entity model."
            )

    definition_binding = model_site_props.get("definition_binding")
    dict_key_references = model_site_props.get("dict_key_references", {}) or {}
    if not isinstance(dict_key_references, dict):
        raise ValueError(
            f"{model_cls.__name__} dict_key_references must be an object"
        )

    # ── Layer 1: Model-level CRUD permissions ─────────────────────────────
    # Config formats:
    #   dict:  {"developer": "crud", "admin": "crud", "user": "crud"}
    #   string legacy: "admin-crud", "crud", "rcud"
    #   not set → all roles get full "crud"
    #
    # Permission chars:
    #   c = can call create API, has create button
    #   r = can call get/get_multi, sees data in list/detail
    #   u = can call update API, has update button
    #   d = can call delete API, has delete button
    # ────────────────────────────────────────────────────────────────────────
    role_permissions = _parse_model_permissions(raw_permissions, model_cls.__name__)
    model_permissions = _compute_flat_perms(role_permissions)

    # ── Layer 3: Frontend visibility ──────────────────────────────────────
    # Config formats:
    #   list:  ["admin", "developer"]   → those roles can see it
    #   dict:  {"user": True, "admin": True, "developer": False}
    #   string legacy: "admin"  → admin+ visible
    #   not set → all roles visible (independent of permissions)
    # ────────────────────────────────────────────────────────────────────────
    role_visible = _parse_visible(raw_visible, role_permissions)

    # Validate union_key is a list of field names
    if union_key is not None:
        if not isinstance(union_key, list):
            console.print(f"[yellow]Warning: union_key should be a list of field names, got {type(union_key)}[/yellow]")
            union_key = None
        elif len(union_key) < 2:
            console.print(
                "[yellow]Warning: union_key should have at least 2 fields "
                "for composite key[/yellow]"
            )
            union_key = None

    fields: List[Dict[str, Any]] = []
    for name, field in model_cls.model_fields.items():
        sa_column_kwargs = getattr(field, "sa_column_kwargs", {})
        if sa_column_kwargs is PydanticUndefined or sa_column_kwargs is None:
            sa_column_kwargs = {}

        info = sa_column_kwargs.get("info", {})
        site_props = info.get("site_props", {})
        # Also support group directly in info (for backward compatibility)
        if "group" in info and not site_props.get("group"):
            site_props = dict(site_props)
            site_props["group"] = info["group"]
        if not site_props:
            json_schema_extra = getattr(field, "json_schema_extra", None)
            if json_schema_extra is PydanticUndefined or json_schema_extra is None:
                json_schema_extra = {}
            if isinstance(json_schema_extra, dict):
                site_props = json_schema_extra.get("site_props", {}) or {}

        if not site_props:
            schema_extra = getattr(field, "schema_extra", None)
            if schema_extra is PydanticUndefined or schema_extra is None:
                schema_extra = {}
            if isinstance(schema_extra, dict):
                site_props = schema_extra.get("site_props", {}) or {}

        if not site_props:
            sa_column = getattr(field, "sa_column", None)
            if sa_column is not None and sa_column is not PydanticUndefined:
                sa_column_info = getattr(sa_column, "info", {})
                if isinstance(sa_column_info, dict):
                    site_props = sa_column_info.get("site_props", {}) or {}

        raw_field_permissions = site_props.get("permissions", None)  # None = inherit from model
        create_optional = site_props.get("create_optional", False)
        update_optional = site_props.get("update_optional", False)
        allow_download = site_props.get("allow_download", True)
        stream_config = site_props.get("stream", {}) or {}
        if not isinstance(stream_config, dict):
            raise ValueError(f"{model_cls.__name__}.{name} site_props.stream must be an object")
        visible_when = _normalize_json_condition(
            site_props.get("visible_when"),
            model_name=model_cls.__name__,
            field_name=name,
            rule_name="visible_when",
        )
        required_when = _normalize_json_condition(
            site_props.get("required_when"),
            model_name=model_cls.__name__,
            field_name=name,
            rule_name="required_when",
        )
        clear_when_hidden = site_props.get("clear_when_hidden", False)
        if not isinstance(clear_when_hidden, bool):
            raise ValueError(
                f"{model_cls.__name__}.{name} site_props.clear_when_hidden must be a boolean"
            )

        # ── Layer 2: Field-level CRU permissions ──────────────────────────
        # Config formats:
        #   dict:  {"developer": "cru", "admin": "cru", "user": "r"}
        #   string: "cru"  (applies to all roles)
        #   not set → inherit from model role_permissions, strip 'd'
        #
        # Permission chars:
        #   c = field can be included in create API request
        #   r = field is returned in get API responses
        #   u = field can be modified in update request
        # Note: 'd' is model-level only, always stripped from field config
        # ────────────────────────────────────────────────────────────────────
        field_role_permissions, permissions = _parse_field_permissions(
            raw_field_permissions, role_permissions, name
        )

        type_annotation = field.annotation
        type_str = str(type_annotation)

        # Unwrap both Optional[X] and the Python 3.10+ X | None syntax before
        # deciding whether this is a structured JSON field.
        _inner, is_optional = _unwrap_optional(type_annotation)

        is_enum = False
        is_multi_select = False
        enum_values: List[Any] = []
        json_kind = None
        json_py_imports: List[str] = []
        json_model_schema = None
        json_item_schema = None
        json_item_kind = None

        if inspect.isclass(_inner) and issubclass(_inner, (str, int)) and hasattr(_inner, "__members__"):
            is_enum = True
            enum_values = [e.value for e in _inner]
            type_str = "str"

        resolved_annotation = _inner
        origin = get_origin(resolved_annotation)
        args = get_args(resolved_annotation)

        if (
            site_props.get("component") == "json"
            and not _is_pydantic_model(_inner)
            and resolved_annotation not in (dict, list)
            and origin not in (dict, list)
        ):
            # ``component=json`` remains a way to opt an otherwise scalar
            # field into a generic JSON editor.  A typed model/collection is
            # authoritative, however, and must retain its Pydantic schema.
            json_kind = site_props.get("json_kind", "object")
            if json_kind == "array":
                type_str = "List[Any]"
            else:
                type_str = "Dict[str, Any]"
        elif resolved_annotation in (dict, list) or origin in (dict, list):
            if resolved_annotation is list or origin is list:
                json_kind = "array"
                item_type, item_optional = _unwrap_optional(args[0] if args else Any)
                item_origin = get_origin(item_type)
                item_args = get_args(item_type)
                if inspect.isclass(item_type) and issubclass(item_type, (str, int)) and hasattr(item_type, "__members__"):
                    # List[Enum] → multi-select enum
                    is_enum = True
                    is_multi_select = True
                    enum_values = [e.value for e in item_type]
                    type_str = "List[str]"
                elif inspect.isclass(item_type) and _is_pydantic_model(item_type):
                    type_str = f"List[{item_type.__name__}]"
                    json_py_imports.append(item_type.__name__)
                    json_item_schema = _build_json_model_schema(item_type)
                elif item_type in (dict,) or item_origin is dict:
                    value_type = item_args[1] if len(item_args) >= 2 else Any
                    if inspect.isclass(value_type) and _is_pydantic_model(value_type):
                        type_str = f"List[Dict[str, {value_type.__name__}]]"
                        json_py_imports.append(value_type.__name__)
                        json_item_schema = _build_json_model_schema(value_type)
                    else:
                        type_str = "List[Dict[str, Any]]"
                else:
                    if item_type is str:
                        type_str = "List[str]"
                    elif item_type is int:
                        type_str = "List[int]"
                    elif item_type is float:
                        type_str = "List[float]"
                    elif item_type is bool:
                        type_str = "List[bool]"
                    elif item_type is date_type:
                        type_str = "List[date]"
                        json_item_kind = "date"
                    elif item_type is datetime_type:
                        type_str = "List[datetime]"
                        json_item_kind = "datetime"
                    elif item_type is time_type:
                        type_str = "List[time]"
                        json_item_kind = "time"
                    else:
                        type_str = "List[Any]"
                if item_optional:
                    type_str = f"List[Optional[{type_str[5:-1]}]]"
            else:
                json_kind = "object"
                value_type, value_optional = _unwrap_optional(
                    args[1] if len(args) >= 2 else Any
                )
                if inspect.isclass(value_type) and _is_pydantic_model(value_type):
                    type_str = f"Dict[str, {value_type.__name__}]"
                    json_py_imports.append(value_type.__name__)
                    json_item_schema = _build_json_model_schema(value_type)
                else:
                    type_str = "Dict[str, Any]"
                if value_optional:
                    type_str = f"Dict[str, Optional[{type_str[10:-1]}]]"
        elif inspect.isclass(_inner) and _is_pydantic_model(_inner):
            json_kind = "object"
            type_str = _inner.__name__
            json_py_imports.append(_inner.__name__)
            json_model_schema = _build_json_model_schema(_inner)
        else:
            # Check the specific datetime module types before the broad datetime
            # match: ``datetime.date`` and ``datetime.time`` both contain the
            # word "datetime" in their representation.  Use the unwrapped
            # annotation too, so Optional[date] is handled correctly.
            if _inner is time_type or "'datetime.time'" in type_str:
                type_str = "time"
            elif _inner is date_type or "'datetime.date'" in type_str:
                type_str = "date"
            elif _inner is datetime_type:
                type_str = "datetime"
            elif "int" in type_str:
                type_str = "int"
            elif "str" in type_str:
                type_str = "str"
            elif "bool" in type_str or type_annotation is bool:
                type_str = "bool"
            elif "float" in type_str:
                type_str = "float"
            elif "datetime" in type_str:
                type_str = "datetime"
            else:
                type_str = "str"

        ui_type = "json" if json_kind else type_str

        json_condition_schema = json_model_schema or json_item_schema
        if not _json_schema_has_conditions(json_condition_schema):
            json_condition_schema = None

        if is_multi_select:
            ui_type = "multi_select"
        elif site_props.get("component") == "textarea":
            ui_type = "textarea"
        elif site_props.get("component") == "image":
            ui_type = "image"
        elif site_props.get("component") == "images":
            ui_type = "images"
        elif site_props.get("component") == "file":
            ui_type = "file"
        elif site_props.get("component") == "video_stream":
            if ui_type != "str":
                raise ValueError(
                    f"{model_cls.__name__}.{name} uses component='video_stream' but "
                    "is not a string field. Store the stream URL in a string field."
                )
            ui_type = "video_stream"
        elif site_props.get("component") == "location":
            if json_kind != "object":
                raise ValueError(
                    f"{model_cls.__name__}.{name} uses component='location' but "
                    "is not an object field. Use the built-in Location model with "
                    "a SQLAlchemy JSON column."
                )
            location_fields = {
                item.get("name") for item in (json_model_schema or {}).get("fields", [])
            }
            if not {"latitude", "longitude"}.issubset(location_fields):
                raise ValueError(
                    f"{model_cls.__name__}.{name} uses component='location' but "
                    "its model does not define latitude and longitude fields."
                )
            ui_type = "location"
        elif ui_type == "str" and (
            name.endswith("_image")
            or name.endswith("_img")
            or name.endswith("_photo")
            or name == "avatar"
            or name == "image"
            or name == "photo"
            or name == "logo"
        ):
            ui_type = "image"
        elif ui_type == "str" and (
            name.endswith("_file")
            or name.endswith("_attachment")
            or name == "file"
            or name == "attachment"
        ):
            ui_type = "file"

        is_search_field = site_props.get("is_search_field", False)

        model_key = _to_snake(model_cls.__name__)

        default_label_key = f"models.{model_key}.fields.{name}"
        label_key = site_props.get("label", default_label_key)
        translations = site_props.get("translations", {})

        # Extract enum value translations
        enum_translations: dict[str, dict[str, str]] = {}
        if is_enum:
            # 1. Model-level translations (per-field, takes priority)
            for lang, lang_pack in model_translations.items():
                if isinstance(lang_pack, dict):
                    enums_section = lang_pack.get("enums", {})
                    if isinstance(enums_section, dict) and name in enums_section:
                        enum_translations[lang] = dict(enums_section[name])
            # 2. Enum-level __i18n__ (fallback, shared across models)
            if hasattr(_inner, "__i18n__") and isinstance(getattr(_inner, "__i18n__"), dict):
                for lang, trans in _inner.__i18n__.items():
                    if isinstance(trans, dict) and lang not in enum_translations:
                        enum_translations[lang] = dict(trans)

        fk_info = None
        declared_foreign_key = getattr(field, "foreign_key", PydanticUndefined)
        is_fk = (
            declared_foreign_key is not PydanticUndefined
            and declared_foreign_key is not None
        ) or bool(site_props.get("is_foreign_key"))
        if is_fk:
            # A declared foreign key is authoritative.  ``*_id`` remains a
            # convenient naming convention, but is not a requirement for a
            # field to be treated as a relationship by the generator.
            fk_table = name[:-3] if name.endswith("_id") else name
            if isinstance(declared_foreign_key, str) and declared_foreign_key:
                fk_table = declared_foreign_key.split(".")[0]

            target_model_class = "".join(word.capitalize() for word in fk_table.split("_"))
            target_service = site_props.get("target_service") or _to_snake(target_model_class)
            target_endpoint = f"{target_service}s"

            reverse_display = site_props.get("reverse_display", True)
            reverse = site_props.get("reverse", {}) or {}
            if not isinstance(reverse, dict):
                console.print(
                    f"[yellow]Warning: {model_cls.__name__}.{name} site_props.reverse "
                    "must be an object; ignoring it.[/yellow]"
                )
                reverse = {}
            # The nested form supersedes the legacy display-only flag.
            if "display" in reverse:
                reverse_display = bool(reverse["display"])
            model_table_name = getattr(model_cls, '__tablename__', None) or _to_snake(model_cls.__name__)
            is_self_referencing = (target_model_class == model_cls.__name__) or (fk_table == model_table_name)
            fk_info = ForeignKeyInfo(
                name=name,
                target_model=target_model_class,
                target_service=target_service,
                target_endpoint=target_endpoint,
                label_field="name",
                reverse_display=reverse_display,
                reverse=reverse,
                cascade=site_props.get("cascade", {}) or {},
                is_self_referencing=is_self_referencing,
            )

        if is_optional:
            type_str = f"Optional[{type_str}]"

        is_unique = False
        if hasattr(field, "json_schema_extra") and field.json_schema_extra and field.json_schema_extra.get("unique"):
            is_unique = True
        elif sa_column_kwargs and sa_column_kwargs.get("unique"):
            is_unique = True
        elif getattr(field, "json_schema_extra", None) and getattr(field, "json_schema_extra", {}).get("unique"):
            is_unique = True
        elif hasattr(field, "unique") and field.unique is not PydanticUndefined and field.unique is not None:
            is_unique = field.unique

        # Check if local storage
        is_local_storage = site_props.get("storage") == "local" or frontend_only

        # Get field group for UI grouping
        field_group = site_props.get("group")

        # Get fixed keys for Dict[str, Model] fields
        json_fixed_keys = site_props.get("fixed_keys")
        json_lock_keys = bool(site_props.get("lock_keys", False))

        stream_protocol = str(stream_config.get("protocol", "auto")).lower()
        supported_stream_protocols = {"auto", "native", "hls", "rtsp"}
        if ui_type == "video_stream" and stream_protocol not in supported_stream_protocols:
            raise ValueError(
                f"{model_cls.__name__}.{name} stream.protocol must be one of: "
                f"{', '.join(sorted(supported_stream_protocols))}"
            )

        stream_boolean_options = {}
        for option, default in {
            "autoplay": False,
            "muted": True,
            "controls": True,
            "reconnect": True,
        }.items():
            value = stream_config.get(option, default)
            if ui_type == "video_stream" and not isinstance(value, bool):
                raise ValueError(
                    f"{model_cls.__name__}.{name} stream.{option} must be a boolean"
                )
            stream_boolean_options[option] = value

        default_value = None if field.default is PydanticUndefined else field.default
        if is_enum and default_value is not None and hasattr(default_value, "value"):
            default_value = default_value.value

        minimum, maximum = _get_numeric_bounds(field)

        fields.append(
            FieldDefinition(
                name=name,
                type=type_str,
                ui_type=ui_type,
                json_kind=json_kind,
                json_model_schema=json_model_schema,
                json_item_schema=json_item_schema,
                json_condition_schema=json_condition_schema,
                json_item_kind=json_item_kind,
                json_fixed_keys=json_fixed_keys,
                json_lock_keys=json_lock_keys,
                visible_when=visible_when,
                required_when=required_when,
                clear_when_hidden=clear_when_hidden,
                py_imports=sorted(set(json_py_imports)),
                permissions=permissions,
                role_permissions=field_role_permissions,
                create_optional=create_optional,
                update_optional=update_optional,
                required=field.is_required(),
                minimum=minimum,
                maximum=maximum,
                default=default_value,
                default_factory=(
                    "list"
                    if getattr(field, "default_factory", None) is list
                    else "dict"
                    if getattr(field, "default_factory", None) is dict
                    else "date"
                    if ui_type == "date" and getattr(field, "default_factory", None) is not None
                    else None
                ),
                is_enum=is_enum,
                is_multi_select=is_multi_select,
                enum_values=enum_values,
                enum_translations=enum_translations,
                is_search_field=is_search_field,
                fk_info=fk_info,
                allow_download=allow_download,
                stream_protocol=stream_protocol,
                stream_autoplay=stream_boolean_options["autoplay"],
                stream_muted=stream_boolean_options["muted"],
                stream_controls=stream_boolean_options["controls"],
                stream_reconnect=stream_boolean_options["reconnect"],
                label_key=label_key,
                translations=translations,
                is_unique=is_unique,
                is_local_storage=is_local_storage,
                group=field_group,
                importable=bool(site_props.get("importable", True)),
                exportable=bool(site_props.get("exportable", True)),
            )
        )

    model_field_names = {field.name for field in fields}

    # Detect the dependent value in a two-column composite FK.  We keep this
    # as raw table/column metadata here; the target model/service is resolved
    # after every model has been introspected.
    table = getattr(model_cls, "__table__", None)
    if table is not None:
        fields_by_name = {field.name: field for field in fields}
        for constraint in table.foreign_key_constraints:
            elements = list(constraint.elements)
            if len(elements) != 2:
                continue
            pairs = []
            for element in elements:
                target_fullname = str(element.target_fullname)
                if "." not in target_fullname:
                    break
                target_table, target_field = target_fullname.rsplit(".", 1)
                pairs.append({
                    "local_field": str(element.parent.name),
                    "target_table": target_table,
                    "target_field": target_field,
                })
            if len(pairs) != 2 or len({pair["target_table"] for pair in pairs}) != 1:
                continue

            parent_pairs = [
                pair for pair in pairs
                if pair["local_field"].endswith("_id")
                and pair["target_field"].endswith("_id")
            ]
            if len(parent_pairs) != 1:
                continue
            parent_pair = parent_pairs[0]
            value_pair = next(pair for pair in pairs if pair is not parent_pair)
            parent_field = fields_by_name.get(parent_pair["local_field"])
            value_field = fields_by_name.get(value_pair["local_field"])
            if parent_field is None or value_field is None or value_field.fk_info is not None:
                continue
            value_field.composite_selector = {
                "target_table": value_pair["target_table"],
                "parent_field": parent_pair["local_field"],
                "filter_field": parent_pair["target_field"],
                "value_field": value_pair["target_field"],
            }

    for field in fields:
        root_controllers = _json_schema_root_controllers(
            field.json_model_schema or field.json_item_schema
        )
        unknown_controllers = sorted(root_controllers - model_field_names)
        if unknown_controllers:
            raise ValueError(
                f"{model_cls.__name__}.{field.name} conditional JSON rules reference "
                f"unknown root field(s): {', '.join(unknown_controllers)}"
            )

    has_explicit_search = any(f.get("is_search_field") for f in fields)
    if not has_explicit_search:
        guess_candidates = ["name", "title", "label", "slug", "email", "username", "full_name"]
        for candidate in guess_candidates:
            found = next((f for f in fields if f["name"] == candidate), None)
            if found:
                found["is_search_field"] = True
                break

    if not any(f.get("is_search_field") for f in fields):
        first_str = next((f for f in fields if f["ui_type"] == "str" and not f["is_enum"]), None)
        if first_str:
            first_str["is_search_field"] = True

    foreign_keys = [f["fk_info"] for f in fields if f["fk_info"]]
    search_field = next((f["name"] for f in fields if f.get("is_search_field")), "id")
    unique_search_field = next((f["name"] for f in fields if f.get("is_search_field") and f.get("is_unique")), None)

    multi_display = _normalize_multi_display(
        model_site_props.get("multi_display"),
        model_name=model_cls.__name__,
        fields=fields,
        default_label_field=search_field,
    )
    model_site_props["multi_display"] = multi_display

    # Validate TimescaleDB / time-series config
    if is_timescaledb:
        if not timescaledb_entity_field:
            console.print(
                f"[red]Error: Model '{model_cls.__name__}' has time_series_table "
                f"but no entity_field configured.[/red]"
            )
            raise ValueError(f"Model '{model_cls.__name__}': time_series_table requires entity_field")
        fk_field_names = {f["name"] for f in foreign_keys}
        if timescaledb_entity_field not in fk_field_names:
            console.print(
                f"[red]Error: Model '{model_cls.__name__}' "
                f"timescaledb_entity_field='{timescaledb_entity_field}' "
                f"must be a foreign key field.[/red]"
            )
            raise ValueError(
                f"Model '{model_cls.__name__}': '{timescaledb_entity_field}' "
                f"is not a foreign key"
            )
        if timescaledb_time_field:
            time_field = next(
                (f for f in fields if f["name"] == timescaledb_time_field),
                None,
            )
            if time_field is None:
                raise ValueError(
                    f"Model '{model_cls.__name__}': time_field "
                    f"'{timescaledb_time_field}' does not exist"
                )
            if time_field["ui_type"] != "datetime":
                raise ValueError(
                    f"Model '{model_cls.__name__}': time_field "
                    f"'{timescaledb_time_field}' must be a datetime field"
                )

    model_site_props["dashboard_metrics"] = _normalize_dashboard_metrics(
        model_site_props.get("dashboard_metrics"),
        model_name=model_cls.__name__,
        fields=fields,
        role_permissions=role_permissions,
    )
    model_site_props["reports"] = _normalize_reports(
        model_site_props.get("reports"),
        model_name=model_cls.__name__,
        fields=fields,
        role_permissions=role_permissions,
    )

    return ModelIntrospectResult(
        fields=fields,
        foreign_keys=foreign_keys,
        search_field=search_field,
        unique_search_field=unique_search_field,
        is_link_table=is_link_table,
        is_singleton=is_singleton,
        model_permissions=model_permissions,
        frontend_only=frontend_only,
        model_translations=model_translations,
        refresh_interval=refresh_interval,
        reverse_fk_display=reverse_fk_display,
        model_site_props=model_site_props,
        actions=actions,
        is_notification_table=is_notification_table,
        union_key=union_key,
        importable=importable,
        exportable=exportable,
        import_key=import_key,
        role_permissions=role_permissions,
        role_visible=role_visible,
        owner_field=owner_field,
        page_edit=page_edit,
        edit_mode=edit_mode,
        list_mode=list_mode,
        multi_display=multi_display,
        is_timescaledb=is_timescaledb,
        timescaledb_entity_field=timescaledb_entity_field,
        timescaledb_metric_field=timescaledb_metric_field,
        timescaledb_time_field=timescaledb_time_field,
        definition_binding=definition_binding,
        dict_key_references=dict_key_references,
    )
