"""Shared validation for model-level and project-level dashboard metrics."""

import re
from typing import Any

from ..naming import to_snake as _to_snake
from ..time_filters import RELATIVE_TIME_PERIODS
from ..types import FieldDefinition
from .permissions import ROLE_ORDER


DASHBOARD_METRIC_AGGREGATIONS = {
    "count", "sum", "avg", "min", "max", "distinct_count",
}


DASHBOARD_METRIC_PERIODS = {*RELATIVE_TIME_PERIODS, "all"}


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
