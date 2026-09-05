"""Validation and normalization of model reporting declarations."""

from typing import Any

from ..types import FieldDefinition
from .permissions import ROLE_ORDER


REPORT_CATEGORIES = {
    "cartesian", "multi_cartesian", "composition", "scatter",
}


REPORT_BINS = {
    "none", "auto", "1m", "5m", "15m", "hour", "day", "week", "month",
}


REPORT_AGGREGATIONS = {
    "raw", "sum", "avg", "min", "max", "median", "count", "distinct_count",
}


REPORT_NUMERIC_TYPES = {"int", "float"}


REPORT_UNSUPPORTED_TYPES = {
    "json", "location", "image", "images", "file", "video_stream", "textarea",
}


def _normalize_reports(
    raw: Any,
    *,
    model_name: str,
    fields: list[FieldDefinition],
    role_permissions: dict[str, str],
) -> dict[str, Any] | None:
    """Validate a model's self-service reporting capability declaration."""
    if raw in (None, False):
        return None
    if raw is True:
        raise ValueError(
            f"Model '{model_name}': reports=true is ambiguous; configure categories and inputs"
        )
    if not isinstance(raw, dict):
        raise ValueError(f"Model '{model_name}': reports must be false or an object")
    if raw.get("enabled", True) is False:
        return None

    prefix = f"Model '{model_name}': reports"
    categories = raw.get("categories")
    if not isinstance(categories, list) or not categories:
        raise ValueError(f"{prefix}.categories must be a non-empty list")
    if any(value not in REPORT_CATEGORIES for value in categories):
        supported = ", ".join(sorted(REPORT_CATEGORIES))
        raise ValueError(f"{prefix}.categories contains an unsupported value; use: {supported}")
    if len(categories) != len(set(categories)):
        raise ValueError(f"{prefix}.categories must not contain duplicates")

    field_map = {field.name: field for field in fields}
    inputs = raw.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError(f"{prefix}.inputs must be an object")

    def resolve_field(field_name: Any, path: str) -> FieldDefinition:
        if not isinstance(field_name, str) or not field_name:
            raise ValueError(f"{path} must use non-empty field names")
        if "." in field_name:
            raise ValueError(
                f"{path}.{field_name} uses a related-field path; report inputs currently "
                "support direct model fields only"
            )
        field = field_map.get(field_name)
        if field is None:
            raise ValueError(f"{path} references unknown field '{field_name}'")
        if field.ui_type in REPORT_UNSUPPORTED_TYPES:
            raise ValueError(
                f"{path}.{field_name} cannot use field type '{field.ui_type}' in reports"
            )
        return field

    normalized_inputs: dict[str, list[dict[str, Any]]] = {
        "x": [], "y": [], "cls": [], "count": [],
    }
    raw_x = inputs.get("x", {})
    if not isinstance(raw_x, dict):
        raise ValueError(f"{prefix}.inputs.x must be an object keyed by field name")
    for field_name, declaration in raw_x.items():
        field = resolve_field(field_name, f"{prefix}.inputs.x")
        if declaration is None:
            declaration = {}
        if not isinstance(declaration, dict):
            raise ValueError(f"{prefix}.inputs.x.{field_name} must be an object")
        bins = declaration.get("bins", ["none"])
        if not isinstance(bins, list) or not bins or any(value not in REPORT_BINS for value in bins):
            raise ValueError(f"{prefix}.inputs.x.{field_name}.bins contains an unsupported bin")
        if len(bins) != len(set(bins)):
            raise ValueError(f"{prefix}.inputs.x.{field_name}.bins must not contain duplicates")
        time_bins = {"1m", "5m", "15m", "hour", "day", "week", "month"}
        if time_bins.intersection(bins) and field.ui_type not in {"date", "datetime"}:
            raise ValueError(f"{prefix}.inputs.x.{field_name} uses time bins on a non-date field")
        normalized_inputs["x"].append({
            "field": field_name,
            "data_type": field.ui_type,
            "bins": bins,
            "readable_roles": [
                role for role in ROLE_ORDER
                if "r" in (field.role_permissions or {}).get(role, "")
            ],
        })

    raw_y = inputs.get("y", {})
    if not isinstance(raw_y, dict):
        raise ValueError(f"{prefix}.inputs.y must be an object keyed by field name")
    for field_name, declaration in raw_y.items():
        field = resolve_field(field_name, f"{prefix}.inputs.y")
        if declaration is None:
            declaration = {}
        if not isinstance(declaration, dict):
            raise ValueError(f"{prefix}.inputs.y.{field_name} must be an object")
        aggregations = declaration.get("aggregations", ["raw"])
        if (
            not isinstance(aggregations, list)
            or not aggregations
            or any(value not in REPORT_AGGREGATIONS for value in aggregations)
        ):
            raise ValueError(
                f"{prefix}.inputs.y.{field_name}.aggregations contains an unsupported aggregation"
            )
        if len(aggregations) != len(set(aggregations)):
            raise ValueError(
                f"{prefix}.inputs.y.{field_name}.aggregations must not contain duplicates"
            )
        numeric_only = {"sum", "avg", "min", "max", "median"}
        if numeric_only.intersection(aggregations) and field.ui_type not in REPORT_NUMERIC_TYPES:
            raise ValueError(
                f"{prefix}.inputs.y.{field_name} uses numeric aggregation on "
                f"'{field.ui_type}'"
            )
        normalized_inputs["y"].append({
            "field": field_name,
            "data_type": field.ui_type,
            "aggregations": aggregations,
            "readable_roles": [
                role for role in ROLE_ORDER
                if "r" in (field.role_permissions or {}).get(role, "")
            ],
        })

    for slot in ("cls", "count"):
        declarations = inputs.get(slot, ["$rows"] if slot == "count" else [])
        if not isinstance(declarations, list) or any(not isinstance(value, str) for value in declarations):
            raise ValueError(f"{prefix}.inputs.{slot} must be a list of field names")
        if len(declarations) != len(set(declarations)):
            raise ValueError(f"{prefix}.inputs.{slot} must not contain duplicates")
        for field_name in declarations:
            if slot == "count" and field_name == "$rows":
                normalized_inputs[slot].append({
                    "field": "$rows", "data_type": "number", "readable_roles": list(ROLE_ORDER),
                })
                continue
            field = resolve_field(field_name, f"{prefix}.inputs.{slot}")
            normalized_inputs[slot].append({
                "field": field_name,
                "data_type": field.ui_type,
                "readable_roles": [
                    role for role in ROLE_ORDER
                    if "r" in (field.role_permissions or {}).get(role, "")
                ],
            })

    required_slots = {
        "cartesian": ("x", "y"),
        "multi_cartesian": ("x", "y", "cls"),
        "composition": ("cls", "count"),
        "scatter": ("x", "y"),
    }
    for category in categories:
        missing = [slot for slot in required_slots[category] if not normalized_inputs[slot]]
        if missing:
            raise ValueError(
                f"{prefix}.categories '{category}' requires configured input(s): {', '.join(missing)}"
            )

    filters = raw.get("filters", [])
    if not isinstance(filters, list) or any(not isinstance(value, str) for value in filters):
        raise ValueError(f"{prefix}.filters must be a list of field names")
    if len(filters) != len(set(filters)):
        raise ValueError(f"{prefix}.filters must not contain duplicates")
    normalized_filters = []
    for field_name in filters:
        field = resolve_field(field_name, f"{prefix}.filters")
        normalized_filters.append({
            "field": field_name,
            "data_type": field.ui_type,
            "label_key": field.label_key,
            "is_enum": field.is_enum,
            "is_multi_select": field.is_multi_select,
            "enum_values": list(field.enum_values),
            "is_foreign_key": field.fk_info is not None,
            "foreign_key": (
                {
                    "target_model": field.fk_info.target_model,
                    "target_service": field.fk_info.target_service,
                    "label_field": field.fk_info.label_field,
                }
                if field.fk_info is not None
                else None
            ),
            "readable_roles": [
                role for role in ROLE_ORDER
                if "r" in (field.role_permissions or {}).get(role, "")
            ],
        })

    readable_roles = [role for role in ROLE_ORDER if "r" in role_permissions.get(role, "")]
    visible = raw.get("visible", readable_roles)
    if not isinstance(visible, list) or any(role not in ROLE_ORDER for role in visible):
        raise ValueError(f"{prefix}.visible must contain only user, admin, or developer")
    permitted_roles = [role for role in ROLE_ORDER if role in visible and role in readable_roles]

    limits = raw.get("limits", {})
    if not isinstance(limits, dict):
        raise ValueError(f"{prefix}.limits must be an object")
    normalized_limits = {
        "max_rows": limits.get("max_rows", 5000),
        "max_series": limits.get("max_series", 20),
        "max_categories": limits.get("max_categories", 100),
        "max_span_days": limits.get("max_span_days", 366),
    }
    for name, value in normalized_limits.items():
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{prefix}.limits.{name} must be a positive integer")

    return {
        "enabled": True,
        "categories": categories,
        "inputs": normalized_inputs,
        "filters": normalized_filters,
        "visible": visible,
        "permitted_roles": permitted_roles,
        "limits": normalized_limits,
    }
