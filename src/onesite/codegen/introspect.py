import inspect
import re
from datetime import date as date_type, datetime as datetime_type, time as time_type
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic_core import PydanticUndefined
from rich.console import Console
from sqlmodel import SQLModel

from .types import FieldDefinition, ForeignKeyInfo, ModelIntrospectResult
from .time_filters import RELATIVE_TIME_PERIODS

console = Console()

def _to_snake(name: str) -> str:
    import re

    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _is_pydantic_model(cls: Any) -> bool:
    """Check if cls is a Pydantic model suitable for JSON schema (excludes DB-backed SQLModels).

    Returns True for plain BaseModel subclasses and SQLModel(table=False),
    but not for SQLModel(table=True) which are real DB tables.
    """
    return (
        inspect.isclass(cls)
        and issubclass(cls, BaseModel)
        and not (issubclass(cls, SQLModel) and getattr(cls, "__table__", None) is not None)
    )


def _json_field_kind_from_annotation(annotation: Any) -> str:
    if annotation is bool:
        return "bool"
    if annotation is int:
        return "int"
    if annotation is float:
        return "float"
    if annotation is str:
        return "str"
    type_str = str(annotation)
    if "datetime" in type_str:
        return "datetime"
    if inspect.isclass(annotation) and issubclass(annotation, Enum):
        return "enum"
    if inspect.isclass(annotation) and _is_pydantic_model(annotation):
        return "model"
    origin = get_origin(annotation)
    if origin is list or annotation is list:
        return "array"
    return "any"


def _get_field_site_props(field: Any) -> Dict[str, Any]:
    """Return OneSite field metadata from SQLModel or Pydantic field info.

    JSON child models are usually ``SQLModel(table=False)`` instances.  They
    do not have a SQL column of their own, but SQLModel still preserves
    ``sa_column_kwargs`` on their FieldInfo, making it the most consistent
    place for nested JSON UI metadata.
    """
    sa_column_kwargs = getattr(field, "sa_column_kwargs", {})
    if sa_column_kwargs is PydanticUndefined or not isinstance(sa_column_kwargs, dict):
        sa_column_kwargs = {}
    info = sa_column_kwargs.get("info", {})
    if not isinstance(info, dict):
        info = {}
    site_props = info.get("site_props", {})
    if not isinstance(site_props, dict):
        site_props = {}
    if "group" in info and not site_props.get("group"):
        site_props = {**site_props, "group": info["group"]}

    if site_props:
        return site_props

    for extra_name in ("json_schema_extra", "schema_extra"):
        extra = getattr(field, extra_name, None)
        if extra is PydanticUndefined or not isinstance(extra, dict):
            continue
        props = extra.get("site_props", {})
        if isinstance(props, dict) and props:
            return props

    sa_column = getattr(field, "sa_column", None)
    if sa_column is not None and sa_column is not PydanticUndefined:
        column_info = getattr(sa_column, "info", {})
        if isinstance(column_info, dict):
            props = column_info.get("site_props", {})
            if isinstance(props, dict):
                return props
    return {}


def _normalize_json_condition(
    value: Any, *, model_name: str, field_name: str, rule_name: str
) -> Dict[str, List[Any]] | None:
    """Validate and normalize a JSON child-field condition declaration."""
    if value is None:
        return None
    if not isinstance(value, dict) or not value:
        raise ValueError(
            f"{model_name}.{field_name} site_props.{rule_name} must be a non-empty object"
        )
    normalized: Dict[str, List[Any]] = {}
    for controller, expected in value.items():
        if not isinstance(controller, str) or not controller:
            raise ValueError(
                f"{model_name}.{field_name} site_props.{rule_name} keys must be non-empty strings"
            )
        values = expected if isinstance(expected, (list, tuple, set)) else [expected]
        if not values or any(isinstance(item, (dict, list, tuple, set)) for item in values):
            raise ValueError(
                f"{model_name}.{field_name} site_props.{rule_name}.{controller} "
                "must be a scalar or a non-empty list of scalars"
            )
        normalized[controller] = list(values)
    return normalized


def _build_json_model_schema(
    model: type[BaseModel], visited: Set[type] | None = None, depth: int = 0
) -> Dict[str, Any]:
    if visited is None:
        visited = set()
    if model in visited or depth >= 2:
        return {"name": model.__name__, "fields": []}
    visited.add(model)
    fields: List[Dict[str, Any]] = []
    for fname, f in model.model_fields.items():
        if fname == "property_key" or fname.startswith("_"):
            continue
        ann = f.annotation
        kind = _json_field_kind_from_annotation(ann)
        field_schema: Dict[str, Any] = {"name": fname, "kind": kind}
        site_props = _get_field_site_props(f)
        visible_when = _normalize_json_condition(
            site_props.get("visible_when"),
            model_name=model.__name__,
            field_name=fname,
            rule_name="visible_when",
        )
        required_when = _normalize_json_condition(
            site_props.get("required_when"),
            model_name=model.__name__,
            field_name=fname,
            rule_name="required_when",
        )
        if visible_when is not None:
            field_schema["visibleWhen"] = visible_when
        if required_when is not None:
            field_schema["requiredWhen"] = required_when
        if "clear_when_hidden" in site_props:
            clear_when_hidden = site_props["clear_when_hidden"]
            if not isinstance(clear_when_hidden, bool):
                raise ValueError(
                    f"{model.__name__}.{fname} site_props.clear_when_hidden must be a boolean"
                )
            field_schema["clearWhenHidden"] = clear_when_hidden
        default = getattr(f, "default", PydanticUndefined)
        if default is not PydanticUndefined and default is not None:
            field_schema["default"] = getattr(default, "value", default)
        if kind == "enum" and inspect.isclass(ann) and issubclass(ann, Enum):
            field_schema["enumValues"] = [e.value for e in ann]
        elif kind == "model" and inspect.isclass(ann) and _is_pydantic_model(ann):
            field_schema["model"] = _build_json_model_schema(ann, visited=visited, depth=depth + 1)
        elif kind == "array":
            origin = get_origin(ann)
            args = get_args(ann) if origin is list else ()
            item_ann = args[0] if args else Any
            item_kind = _json_field_kind_from_annotation(item_ann)
            item_schema: Dict[str, Any] = {"kind": item_kind}
            if item_kind == "enum" and inspect.isclass(item_ann) and issubclass(item_ann, Enum):
                item_schema["enumValues"] = [e.value for e in item_ann]
            elif item_kind == "model" and inspect.isclass(item_ann) and _is_pydantic_model(item_ann):
                item_schema["model"] = _build_json_model_schema(item_ann, visited=visited, depth=depth + 1)
            field_schema["item"] = item_schema
        fields.append(field_schema)
    return {"name": model.__name__, "fields": fields}


def _json_schema_has_conditions(schema: Dict[str, Any] | None) -> bool:
    """Whether a JSON editor schema includes any conditional child field."""
    if not schema:
        return False
    for field in schema.get("fields", []):
        if field.get("visibleWhen") or field.get("requiredWhen"):
            return True
        if _json_schema_has_conditions(field.get("model")):
            return True
        item = field.get("item")
        if isinstance(item, dict) and _json_schema_has_conditions(item.get("model")):
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════
# Three-layer permission system
# ═══════════════════════════════════════════════════════════════════════════

ROLE_ORDER = ["user", "admin", "developer"]
ROLE_LEVELS = {"user": 0, "admin": 1, "developer": 2}

DASHBOARD_METRIC_AGGREGATIONS = {
    "count", "sum", "avg", "min", "max", "distinct_count",
}
DASHBOARD_METRIC_PERIODS = {*RELATIVE_TIME_PERIODS, "all"}

DATA_REPORT_BUCKETS = {"raw", "auto", "1m", "5m", "15m", "1h", "6h", "1d", "1w"}
DATA_REPORT_AGGREGATIONS = {"avg", "min", "max", "sum", "count"}
DATA_REPORT_VIEWS = {
    "auto", "line", "area", "bar", "stacked_bar", "pie", "scatter",
    "histogram", "heatmap", "status",
}


def _normalize_data_reports(
    raw: Any,
    *,
    model_name: str,
    fields: list[FieldDefinition],
    role_permissions: dict[str, str],
    timeseries_config: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Validate report declarations and resolve their time-series fields."""
    if raw in (None, False):
        return []
    if not timeseries_config:
        raise ValueError(f"Model '{model_name}': data_reports currently require time_series_table")

    # The common case is intentionally one line: ``data_reports = True``.
    # A dict customises the inferred report; a list remains available for
    # models that expose more than one report.
    if raw is True:
        raw = [{}]
    elif isinstance(raw, dict):
        raw = [raw]
    elif not isinstance(raw, list):
        raise ValueError(f"Model '{model_name}': data_reports must be true, an object, or a list")

    field_map = {field.name: field for field in fields}
    readable_roles = {role for role, perms in role_permissions.items() if "r" in perms}
    seen_keys: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        prefix = f"Model '{model_name}': data_reports[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{prefix} must be an object")
        report = dict(item)
        key = report.get("key", _to_snake(model_name))
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError(f"{prefix}.key must be a valid identifier")
        if key in seen_keys:
            raise ValueError(f"{prefix}.key duplicates '{key}'")
        seen_keys.add(key)
        title = report.get("title", model_name)
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"{prefix}.title must be a non-empty string")

        resolved_fields = {
            "entity_field": report.get("entity_field", timeseries_config.get("entity_field")),
            "metric_field": report.get("metric_field", timeseries_config.get("metric_field")),
            "time_field": report.get("time_field", timeseries_config.get("time_field")),
            "value_field": report.get("value_field", "value"),
        }
        for name, field_name in resolved_fields.items():
            if not isinstance(field_name, str) or field_name not in field_map:
                raise ValueError(f"{prefix}.{name} references unknown field '{field_name}'")
        if field_map[resolved_fields["time_field"]].ui_type != "datetime":
            raise ValueError(f"{prefix}.time_field must reference a datetime field")

        value_path = report.get("value_path", "value")
        if not isinstance(value_path, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value_path):
            raise ValueError(f"{prefix}.value_path must be a simple JSON key")
        buckets = report.get("buckets", ["raw", "auto", "5m", "1h", "1d"])
        aggregations = report.get("aggregations", ["avg", "min", "max", "count"])
        if not isinstance(buckets, list) or not buckets or any(v not in DATA_REPORT_BUCKETS for v in buckets):
            raise ValueError(f"{prefix}.buckets contains an unsupported bucket")
        if not isinstance(aggregations, list) or not aggregations or any(v not in DATA_REPORT_AGGREGATIONS for v in aggregations):
            raise ValueError(f"{prefix}.aggregations contains an unsupported aggregation")
        views = report.get("views", "auto")
        if isinstance(views, str):
            views = [views]
        if not isinstance(views, list) or not views or any(v not in DATA_REPORT_VIEWS for v in views):
            raise ValueError(f"{prefix}.views contains an unsupported report view")
        visible = report.get("visible", sorted(readable_roles, key=ROLE_ORDER.index))
        if not isinstance(visible, list) or any(role not in ROLE_ORDER for role in visible):
            raise ValueError(f"{prefix}.visible must contain only user, admin, or developer")
        permitted_roles = [role for role in ROLE_ORDER if role in visible and role in readable_roles]
        max_span_days = report.get("max_span_days", 90)
        if isinstance(max_span_days, bool) or not isinstance(max_span_days, int) or max_span_days <= 0:
            raise ValueError(f"{prefix}.max_span_days must be a positive integer")
        report.update(
            key=key,
            title=title,
            **resolved_fields,
            value_path=value_path,
            buckets=buckets,
            aggregations=aggregations,
            views=views,
            visible=visible,
            permitted_roles=permitted_roles,
            max_span_days=max_span_days,
        )
        normalized.append(report)
    return normalized


def _normalize_dashboard_metric_calculation(
    raw: dict[str, Any],
    *,
    prefix: str,
    field_map: dict[str, FieldDefinition],
) -> dict[str, Any]:
    """Validate one aggregate value used by a Dashboard KPI card."""
    aggregation = raw.get("aggregation", "count")
    if aggregation not in DASHBOARD_METRIC_AGGREGATIONS:
        supported = ", ".join(sorted(DASHBOARD_METRIC_AGGREGATIONS))
        raise ValueError(f"{prefix}.aggregation must be one of: {supported}")

    field_name = raw.get("field")
    if aggregation != "count" and not field_name:
        raise ValueError(f"{prefix}.field is required for {aggregation}")
    if field_name and field_name not in field_map:
        raise ValueError(f"{prefix}.field '{field_name}' does not exist")
    if (
        field_name
        and aggregation in {"sum", "avg", "min", "max"}
        and field_map[field_name].ui_type not in {"int", "float"}
    ):
        raise ValueError(f"{prefix}.field '{field_name}' must be numeric for {aggregation}")

    # ``time_field`` + ``period`` is the legacy KPI form. Normalize it into
    # the relative-time ``where`` predicate used by every KPI calculation.
    time_field = raw.get("time_field")
    if time_field and time_field not in field_map:
        raise ValueError(f"{prefix}.time_field '{time_field}' does not exist")
    if time_field and field_map[time_field].ui_type not in ("date", "datetime"):
        raise ValueError(f"{prefix}.time_field '{time_field}' must be a date or datetime field")

    period = raw.get("period", "all")
    if period not in DASHBOARD_METRIC_PERIODS:
        supported = ", ".join(sorted(DASHBOARD_METRIC_PERIODS))
        raise ValueError(f"{prefix}.period must be one of: {supported}")
    if period != "all" and not time_field:
        raise ValueError(f"{prefix}.time_field is required when period is '{period}'")

    where = raw.get("where", {})
    if not isinstance(where, dict):
        raise ValueError(f"{prefix}.where must be an object")
    where = dict(where)
    if time_field and period != "all":
        existing_time_filter = where.get(time_field)
        relative_filter = {"period": period}
        if existing_time_filter is not None and existing_time_filter != relative_filter:
            raise ValueError(f"{prefix}.time_field conflicts with where.{time_field}")
        where[time_field] = relative_filter

    relative_time_fields: list[str] = []
    for filter_field, value in where.items():
        if filter_field not in field_map:
            raise ValueError(f"{prefix}.where field '{filter_field}' does not exist")
        if isinstance(value, dict):
            if set(value) != {"period"} or value["period"] not in RELATIVE_TIME_PERIODS:
                supported = ", ".join(sorted(RELATIVE_TIME_PERIODS))
                raise ValueError(
                    f"{prefix}.where.{filter_field} must be a scalar, list, or "
                    f"{{'period': <period>}} where period is one of: {supported}"
                )
            if field_map[filter_field].ui_type not in ("date", "datetime"):
                raise ValueError(
                    f"{prefix}.where.{filter_field} relative time filters require "
                    "a date or datetime field"
                )
            relative_time_fields.append(filter_field)
        elif isinstance(value, (tuple, set)):
            raise ValueError(f"{prefix}.where.{filter_field} must be a scalar or list")
    if len(relative_time_fields) > 1:
        raise ValueError(f"{prefix}.where supports at most one relative time filter")

    compare = raw.get("compare")
    if compare not in (None, "previous_period"):
        raise ValueError(f"{prefix}.compare currently only supports 'previous_period'")
    if compare and not relative_time_fields:
        raise ValueError(f"{prefix}.compare requires a bounded relative time filter")

    fmt = raw.get("format", {"type": "number"})
    if not isinstance(fmt, dict) or fmt.get("type", "number") not in {"number", "currency", "percent"}:
        raise ValueError(f"{prefix}.format.type must be number, currency, or percent")
    decimals = fmt.get("decimals")
    if decimals is not None and (not isinstance(decimals, int) or isinstance(decimals, bool) or decimals < 0):
        raise ValueError(f"{prefix}.format.decimals must be a non-negative integer")

    normalized = {"aggregation": aggregation, "where": where, "format": fmt}
    if field_name:
        normalized["field"] = field_name
    if compare:
        normalized["compare"] = compare
    return normalized


def _normalize_dashboard_metrics(
    raw: Any,
    *,
    model_name: str,
    fields: list[FieldDefinition],
    role_permissions: dict[str, str],
) -> list[dict[str, Any]]:
    """Validate and normalize model-level Dashboard KPI declarations."""
    if raw in (None, False):
        return []
    if not isinstance(raw, list):
        raise ValueError(f"Model '{model_name}': dashboard_metrics must be a list")

    field_map = {field.name: field for field in fields}
    readable_roles = {role for role, perms in role_permissions.items() if "r" in perms}
    seen_keys: set[str] = set()
    normalized: list[dict[str, Any]] = []

    for index, item in enumerate(raw):
        prefix = f"Model '{model_name}': dashboard_metrics[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{prefix} must be an object")

        metric = dict(item)
        key = metric.get("key")
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError(f"{prefix}.key must be a valid identifier")
        if key in seen_keys:
            raise ValueError(f"{prefix}.key duplicates '{key}'")
        seen_keys.add(key)

        title = metric.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"{prefix}.title must be a non-empty string")

        items = metric.get("items")
        if items is None:
            metric.update(_normalize_dashboard_metric_calculation(
                metric, prefix=prefix, field_map=field_map,
            ))
        else:
            if not isinstance(items, list) or len(items) < 2:
                raise ValueError(f"{prefix}.items must be a list with at least two KPI calculations")
            separator = metric.get("separator", " / ")
            if not isinstance(separator, str) or not separator:
                raise ValueError(f"{prefix}.separator must be a non-empty string")
            normalized_items = []
            for item_index, calculation in enumerate(items):
                item_prefix = f"{prefix}.items[{item_index}]"
                if not isinstance(calculation, dict):
                    raise ValueError(f"{item_prefix} must be an object")
                normalized_calculation = _normalize_dashboard_metric_calculation(
                    calculation, prefix=item_prefix, field_map=field_map,
                )
                if normalized_calculation.get("compare"):
                    raise ValueError(f"{item_prefix}.compare is not supported for combined KPIs")
                normalized_items.append(normalized_calculation)
            metric["items"] = normalized_items
            metric["separator"] = separator
            for calculation_key in (
                "aggregation", "field", "where", "time_field", "period", "compare", "format",
            ):
                metric.pop(calculation_key, None)

        visible = metric.get("visible", sorted(readable_roles, key=ROLE_ORDER.index))
        if not isinstance(visible, list) or any(role not in ROLE_ORDER for role in visible):
            raise ValueError(f"{prefix}.visible must contain only user, admin, or developer")
        permitted_roles = [role for role in ROLE_ORDER if role in visible and role in readable_roles]

        order = metric.get("order", index)
        if not isinstance(order, (int, float)) or isinstance(order, bool):
            raise ValueError(f"{prefix}.order must be a number")
        for optional_text in ("icon", "color", "link"):
            value = metric.get(optional_text)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{prefix}.{optional_text} must be a string")
        icon = metric.get("icon", "Activity")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", icon):
            raise ValueError(f"{prefix}.icon must be a valid Lucide component name")

        metric.update(
            visible=visible,
            permitted_roles=permitted_roles,
            icon=icon,
            color=metric.get("color", "blue"),
            order=order,
            i18n_key=f"dashboard.metrics.{_to_snake(model_name)}.{key}",
        )
        metric.pop("time_field", None)
        metric.pop("period", None)
        normalized.append(metric)

    normalized.sort(key=lambda metric: (metric["order"], metric["key"]))
    return normalized


def _parse_model_permissions(raw: Any, model_name: str) -> dict[str, str]:
    """Layer 1: Parse model-level CRUD permissions.

    Returns a dict like {"user": "crud", "admin": "crud", "developer": "crud"}.
    """
    if isinstance(raw, dict):
        return {role: raw.get(role, "") for role in ROLE_ORDER}

    if isinstance(raw, str):
        # Legacy string: "admin-crud", "crud/rcud", or bare "admin"/"user"
        if raw == "admin":
            console.print(
                f"[yellow]Warning: Model '{model_name}' uses legacy 'admin', "
                f"please use 'admin-crud'[/yellow]"
            )
            raw = "admin-crud"
        elif raw == "user":
            console.print(
                f"[yellow]Warning: Model '{model_name}' uses legacy 'user', "
                f"please use 'crud'[/yellow]"
            )
            raw = "crud"

        parts = raw.split("-", 1)
        if len(parts) == 2:
            prefix_role, perm_chars = parts
        else:
            prefix_role, perm_chars = "user", parts[0]

        min_level = ROLE_LEVELS.get(prefix_role, 0)
        return {
            role: perm_chars if ROLE_LEVELS[role] >= min_level else ""
            for role in ROLE_ORDER
        }

    # Default: full access for all
    return {role: "crud" for role in ROLE_ORDER}


def _compute_flat_perms(role_permissions: dict[str, str]) -> str:
    """Derive a flat permission string as the UNION of all roles' permissions.

    Used for backward-compat template code — includes any permission character
    that at least one role possesses, so schemas include all fields that any
    role can access.
    """
    canonical_order = "crud"
    chars: set[str] = set()
    for perms in role_permissions.values():
        chars.update(perms)
    return "".join(c for c in canonical_order if c in chars)


def _parse_visible(raw: Any, role_permissions: dict[str, str] | None = None) -> dict[str, bool]:
    """Layer 3: Parse frontend visibility config.

    Config formats (in priority order):
      list:  ["admin", "developer"]   → only those roles can see it
      dict:  {"user": True, "admin": True, "developer": False}
      string legacy: "admin"  → admin+ visible

    Default fallback: a role is visible if it has any model-level permission.
    This keeps backward compat — models with restricted permissions are
    automatically hidden from unauthorized roles unless explicitly overridden.
    """
    if isinstance(raw, list):
        return {role: role in raw for role in ROLE_ORDER}

    if isinstance(raw, dict):
        return {role: bool(raw.get(role, False)) for role in ROLE_ORDER}

    if isinstance(raw, str) and raw in ROLE_ORDER:
        min_idx = ROLE_ORDER.index(raw)
        return {role: i >= min_idx for i, role in enumerate(ROLE_ORDER)}

    # Default: visible if role has any model permission
    if role_permissions is not None:
        return {role: bool(role_permissions.get(role, "")) for role in ROLE_ORDER}
    return {role: True for role in ROLE_ORDER}


def _parse_field_permissions(
    raw: Any,
    model_role_permissions: dict[str, str],
    field_name: str,
) -> tuple[dict[str, str], str]:
    """Layer 2: Parse field-level CRU permissions.

    Returns (field_role_permissions, flat_permission_string).

    Inherits from model-level when not set, strips 'd' (delete is model-level).
    Special defaults for id (hidden), created_at (r), updated_at (ru).
    """
    # Special field defaults
    if raw is None:
        if field_name == "id":
            return {role: "" for role in ROLE_ORDER}, ""
        if field_name == "created_at":
            return {role: "r" for role in ROLE_ORDER}, "r"
        if field_name == "updated_at":
            return {role: "ru" for role in ROLE_ORDER}, "ru"

    if raw is None:
        # Inherit from model-level, strip 'd'
        result = {
            role: perms.replace("d", "")
            for role, perms in model_role_permissions.items()
        }
    elif isinstance(raw, dict):
        # Per-role dict: missing roles inherit from model, strip 'd'
        result = {}
        for role in ROLE_ORDER:
            perms = raw.get(role, model_role_permissions.get(role, ""))
            result[role] = perms.replace("d", "")
    elif isinstance(raw, str):
        perms = raw.replace("d", "")
        result = {role: perms for role in ROLE_ORDER}
    else:
        result = {role: "cru" for role in ROLE_ORDER}

    flat = _compute_flat_perms(result)
    return result, flat


def get_model_fields(
    model_cls: type[SQLModel], module_name: str | None = None
) -> ModelIntrospectResult:
    model_site_props: Dict[str, Any] = {}
    if hasattr(model_cls, "__onesite__") and isinstance(getattr(model_cls, "__onesite__"), dict):
        model_site_props.update(getattr(model_cls, "__onesite__"))
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
    raw_visible = model_site_props.get("visible", None)
    # ``page_edit`` is the legacy boolean spelling.  ``edit_mode`` is the
    # extensible form and supports modal (default), page, and right-side drawer.
    raw_edit_mode = model_site_props.get("edit_mode")
    if raw_edit_mode is None:
        edit_mode = "page" if model_site_props.get("page_edit", False) else "modal"
    elif isinstance(raw_edit_mode, str) and raw_edit_mode in {"modal", "page", "drawer"}:
        edit_mode = raw_edit_mode
    else:
        raise ValueError(
            f"Invalid edit_mode for {model_cls.__name__}: {raw_edit_mode!r}. "
            "Expected 'modal', 'page', or 'drawer'."
        )
    page_edit = edit_mode == "page"
    owner_field = model_site_props.get("owner_field", None)  # FK field name for user-owner filtering

    # ── TimescaleDB / time-series config ──────────────────────────────────
    # New nested format:  __onesite__ = {"time_series_table": {"entity_field": ..., "metric_field": ..., ...}}
    # Legacy flat format: __onesite__ = {"is_timescaledb": True, "timescaledb_entity_field": ...}
    ts_config = model_site_props.get("time_series_table")
    if ts_config:
        is_timescaledb = True
        timescaledb_entity_field = ts_config.get("entity_field")
        timescaledb_metric_field = ts_config.get("metric_field")
        timescaledb_time_field = ts_config.get("time_field")
        timescaledb_model_table = ts_config.get("model_table")
        property_config = ts_config.get("property_config")
    else:
        is_timescaledb = bool(model_site_props.get("is_timescaledb", False))
        timescaledb_entity_field = model_site_props.get("timescaledb_entity_field", None)
        timescaledb_metric_field = model_site_props.get("timescaledb_metric_field", None)
        timescaledb_time_field = model_site_props.get("timescaledb_time_field", None)
        timescaledb_model_table = model_site_props.get("timescaledb_model_table", None)
        property_config = None

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
            console.print(f"[yellow]Warning: union_key should have at least 2 fields for composite key[/yellow]")
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

        # Unwrap Optional[X] → X for enum detection
        _inner = type_annotation
        if get_origin(type_annotation) is Union:
            _union_args = [a for a in get_args(type_annotation) if a is not type(None)]
            if len(_union_args) == 1:
                _inner = _union_args[0]

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

        resolved_annotation = type_annotation
        origin = get_origin(resolved_annotation)
        args = get_args(resolved_annotation)

        if site_props.get("component") == "json":
            json_kind = site_props.get("json_kind", "object")
            if json_kind == "array":
                type_str = "List[Any]"
            else:
                type_str = "Dict[str, Any]"
        elif resolved_annotation in (dict, list) or origin in (dict, list):
            if resolved_annotation is list or origin is list:
                json_kind = "array"
                item_type = args[0] if args else Any
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
            else:
                json_kind = "object"
                value_type = args[1] if len(args) >= 2 else Any
                if inspect.isclass(value_type) and _is_pydantic_model(value_type):
                    type_str = f"Dict[str, {value_type.__name__}]"
                    json_py_imports.append(value_type.__name__)
                    json_item_schema = _build_json_model_schema(value_type)
                else:
                    type_str = "Dict[str, Any]"
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
                is_self_referencing=is_self_referencing,
            )

        origin = get_origin(resolved_annotation)
        args = get_args(resolved_annotation)
        is_optional = origin is Union and any(a is type(None) for a in args)
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
                py_imports=sorted(set(json_py_imports)),
                permissions=permissions,
                role_permissions=field_role_permissions,
                create_optional=create_optional,
                update_optional=update_optional,
                required=field.is_required(),
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
    model_site_props["data_reports"] = _normalize_data_reports(
        model_site_props.get("data_reports"),
        model_name=model_cls.__name__,
        fields=fields,
        role_permissions=role_permissions,
        timeseries_config=ts_config,
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
        is_timescaledb=is_timescaledb,
        timescaledb_entity_field=timescaledb_entity_field,
        timescaledb_metric_field=timescaledb_metric_field,
        timescaledb_time_field=timescaledb_time_field,
        timescaledb_model_table=timescaledb_model_table,
        property_config=property_config,
    )
