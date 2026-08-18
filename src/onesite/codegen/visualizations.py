"""Load and compile project-level visualization declarations."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

from ..visualization import DashboardMetric, DataBinding, Visualization
from .time_filters import RELATIVE_TIME_PERIODS
from .types import FieldDefinition, ModelDefinition


ROLE_ORDER = ("user", "admin", "developer")
NUMERIC_UI_TYPES = {"int", "float"}
AGGREGATIONS = {"count", "distinct_count", "sum", "avg", "min", "max"}
TIME_BUCKETS = {
    "minute", "hour", "day", "week", "month", "year",
    "1m", "5m", "15m", "1h", "1d",
}
TIME_EXTRACTS = {"hour", "weekday", "day", "week", "month", "quarter", "year"}
FILTER_TYPES = {"select", "multi_select", "date_range", "number_range"}
PRESETS: dict[str, dict[str, Any]] = {
    "line.basic": {"contract": "xy", "renderer": "line", "required": {"x", "y"}},
    "line.smooth": {"contract": "xy", "renderer": "line", "required": {"x", "y"}},
    "line.area": {"contract": "xy", "renderer": "line", "required": {"x", "y"}},
    "line.stacked": {"contract": "xy_series", "renderer": "line", "required": {"x", "y"}},
    "line.stacked_area": {"contract": "xy_series", "renderer": "line", "required": {"x", "y"}},
    "line.stacked_area_gradient": {"contract": "xy_series", "renderer": "line", "required": {"x", "y"}},
    "scatter.basic": {"contract": "xy", "renderer": "scatter", "required": {"x", "y"}},
    "scatter.category": {"contract": "xy_series", "renderer": "scatter", "required": {"x", "y", "series"}},
    "pie.donut": {"contract": "category_value", "renderer": "pie", "required": {"category", "value"}},
    "pie.rounded_donut": {"contract": "category_value", "renderer": "pie", "required": {"category", "value"}},
    "pie.half_donut": {"contract": "category_value", "renderer": "pie", "required": {"category", "value"}},
    "heatmap.cartesian": {"contract": "xyz", "renderer": "heatmap", "required": {"x", "y", "value"}},
    "radar.basic": {"contract": "radar", "renderer": "radar", "required": {"indicator", "series", "value"}},
    "tree.basic": {"contract": "hierarchy", "renderer": "tree", "required": {"id", "parent", "name"}},
    "treemap.basic": {"contract": "hierarchy", "renderer": "treemap", "required": {"id", "parent", "name", "value"}},
    "sunburst.basic": {"contract": "hierarchy", "renderer": "sunburst", "required": {"id", "parent", "name", "value"}},
    "sankey.basic": {"contract": "links", "renderer": "sankey", "required": {"source", "target", "value"}},
}

CONTRACT_INPUTS = {
    "xy": {"x", "y", "label", "tooltip"},
    "xy_series": {"x", "series", "y", "label", "tooltip"},
    "category_value": {"category", "value", "tooltip"},
    "xyz": {"x", "y", "value", "tooltip"},
    "radar": {"indicator", "series", "value", "max"},
    "hierarchy": {"id", "parent", "name", "value"},
    "links": {"source", "target", "value", "source_name", "target_name"},
}


def _fail(key: str, message: str) -> ValueError:
    return ValueError(f"Visualization '{key}': {message}")


def _load_project_module(cwd: Path) -> tuple[Path, Any] | None:
    """Import the project's visualization declaration module once per load."""

    path = cwd / "visualizations.py"
    if not path.exists():
        return None
    module_name = f"_onesite_project_visualizations_{abs(hash(path.resolve()))}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise ValueError(f"Unable to import {path}: {exc}") from exc
    finally:
        sys.modules.pop(module_name, None)

    return path, module


def _load_declaration_list(
    cwd: Path,
    name: str,
    accepted_type: type,
    description: str,
    *,
    required: bool,
) -> list[dict[str, Any]]:
    loaded = _load_project_module(cwd)
    if loaded is None:
        return []
    path, module = loaded
    raw = getattr(module, name, None)
    if raw is None:
        if required:
            raise ValueError(f"{path} must define a '{name}' list")
        return []
    if not isinstance(raw, (list, tuple)):
        raise ValueError(f"{path}: '{name}' must be a list")
    declarations: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        if isinstance(item, accepted_type):
            declarations.append(item.to_dict())
        elif isinstance(item, dict):
            declarations.append(dict(item))
        else:
            raise ValueError(
                f"{path}: {name}[{index}] must be {description} or a dictionary"
            )
    return declarations


def load_visualizations(cwd: Path) -> list[dict[str, Any]]:
    """Import chart declarations from ``visualizations.py``."""

    return _load_declaration_list(
        cwd, "visualizations", Visualization, "chart(...)", required=True
    )


def load_dashboard_metrics(cwd: Path) -> list[dict[str, Any]]:
    """Import project-level KPI declarations from ``visualizations.py``."""

    return _load_declaration_list(
        cwd, "dashboard_metrics", DashboardMetric, "dashboard_metric(...)", required=False
    )


def _model_lookup(models: Iterable[ModelDefinition]) -> dict[str, ModelDefinition]:
    lookup: dict[str, ModelDefinition] = {}
    for model in models:
        for name in (model["name"], model["module_name"], model["table_name"]):
            lookup[str(name).lower()] = model
    return lookup


def _find_field(model: ModelDefinition, name: str) -> FieldDefinition | None:
    return next((field for field in model.get("fields", []) if field["name"] == name), None)


def _forward_relation(model: ModelDefinition, segment: str) -> tuple[dict, str] | None:
    normalized = segment.lower()
    matches = []
    for fk in model.get("foreign_keys", []):
        names = {
            str(fk["name"]).lower(),
            str(fk["name"]).removesuffix("_id").lower(),
            str(fk["target_model"]).lower(),
            str(fk.get("target_service", "")).lower(),
        }
        if normalized in names:
            matches.append((fk, "forward"))
    if len(matches) > 1:
        raise ValueError(f"relation segment '{segment}' is ambiguous on {model['name']}")
    return matches[0] if matches else None


def _reverse_relation(model: ModelDefinition, segment: str) -> tuple[dict, str] | None:
    normalized = segment.lower()
    matches = []
    for relation in model.get("reverse_foreign_keys", []):
        names = {
            str(relation.get("name", "")).lower(),
            str(relation.get("write_name", "")).lower(),
            str(relation.get("source_model", "")).lower(),
            str(relation.get("source_service", "")).lower(),
        }
        if normalized in names:
            matches.append((relation, "reverse"))
    if len(matches) > 1:
        raise ValueError(f"reverse relation segment '{segment}' is ambiguous on {model['name']}")
    return matches[0] if matches else None


def _resolve_field_path(
    key: str,
    base_model: ModelDefinition,
    raw_path: str,
    lookup: dict[str, ModelDefinition],
) -> tuple[dict[str, Any], list[ModelDefinition]]:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise _fail(key, "field paths must be non-empty strings")
    segments = raw_path.split(".")
    current = base_model
    referenced = [base_model]
    joins: list[dict[str, Any]] = []

    for segment in segments[:-1]:
        relation = _forward_relation(current, segment) or _reverse_relation(current, segment)
        if relation is None:
            raise _fail(key, f"field path '{raw_path}' cannot resolve relation '{segment}' on {current['name']}")
        relation_info, direction = relation
        if direction == "forward":
            target = lookup.get(str(relation_info["target_model"]).lower())
            if target is None:
                raise _fail(key, f"field path '{raw_path}' references unknown model '{relation_info['target_model']}'")
            joins.append({
                "direction": "forward",
                "left_module": current["source_module"],
                "left_model": current["name"],
                "left_field": relation_info["name"],
                "right_module": target["source_module"],
                "right_model": target["name"],
                "right_field": "id",
            })
        else:
            target = lookup.get(str(relation_info["source_model"]).lower())
            if target is None:
                raise _fail(key, f"field path '{raw_path}' references unknown model '{relation_info['source_model']}'")
            joins.append({
                "direction": "reverse",
                "left_module": current["source_module"],
                "left_model": current["name"],
                "left_field": "id",
                "right_module": target["source_module"],
                "right_model": target["name"],
                "right_field": relation_info["source_fk_field"],
            })
        current = target
        if current not in referenced:
            referenced.append(current)

    field = _find_field(current, segments[-1])
    if field is None:
        raise _fail(key, f"field path '{raw_path}' references unknown field '{current['name']}.{segments[-1]}'")
    return ({
        "path": raw_path,
        "module": current["source_module"],
        "model": current["name"],
        "field": field["name"],
        "field_type": field.get("ui_type", "any"),
        "joins": joins,
    }, referenced)


def _binding_dict(key: str, value: Any) -> dict[str, Any]:
    if isinstance(value, DataBinding):
        value = value.to_dict()
    if not isinstance(value, dict):
        raise _fail(key, "chart inputs must use dim(...), metric(...), count(), or dictionaries")
    result = dict(value)
    kind = result.get("kind")
    if kind not in {"dimension", "metric"}:
        raise _fail(key, f"input binding kind must be 'dimension' or 'metric', got {kind!r}")
    return result


def _field_readable_roles(field: FieldDefinition) -> set[str]:
    configured = field.get("role_permissions")
    if isinstance(configured, dict):
        return {role for role in ROLE_ORDER if "r" in configured.get(role, "")}
    return set(ROLE_ORDER) if "r" in field.get("permissions", "") else set()


def _compile_binding(
    key: str,
    value: Any,
    base_model: ModelDefinition,
    lookup: dict[str, ModelDefinition],
) -> tuple[dict[str, Any], list[ModelDefinition], set[str]]:
    binding = _binding_dict(key, value)
    aggregate = binding.get("aggregate")
    if binding["kind"] == "metric":
        if aggregate not in AGGREGATIONS:
            raise _fail(key, f"metric aggregate must be one of {', '.join(sorted(AGGREGATIONS))}")
    elif aggregate is not None:
        raise _fail(key, "dimension bindings cannot define aggregate")

    compiled = {name: binding[name] for name in ("kind", "aggregate", "label", "bucket", "extract", "unit") if binding.get(name) is not None}
    referenced = [base_model]
    readable_roles = set(ROLE_ORDER)
    field_path = binding.get("field")
    if field_path is None:
        if binding["kind"] != "metric" or aggregate != "count":
            raise _fail(key, "only count() may omit a field")
        compiled.update({"field": None, "joins": [], "field_type": "int"})
    else:
        resolved, referenced = _resolve_field_path(key, base_model, field_path, lookup)
        compiled.update(resolved)
        target_model = referenced[-1]
        target_field = _find_field(target_model, resolved["field"])
        if target_field is not None:
            readable_roles &= _field_readable_roles(target_field)
            if target_field.get("is_enum"):
                compiled["enum_i18n_key"] = (
                    f"models.{target_model['module_name']}.enums.{target_field['name']}"
                )

    if binding.get("bucket") is not None:
        if binding["bucket"] not in TIME_BUCKETS:
            raise _fail(key, f"unsupported time bucket '{binding['bucket']}'")
        if compiled.get("field_type") not in {"date", "datetime"}:
            raise _fail(key, "bucket can only be used with date or datetime fields")
    if binding.get("extract") is not None:
        if binding["extract"] not in TIME_EXTRACTS:
            raise _fail(key, f"unsupported time extract '{binding['extract']}'")
        if compiled.get("field_type") not in {"date", "datetime"}:
            raise _fail(key, "extract can only be used with date or datetime fields")
    if aggregate in {"sum", "avg"} and compiled.get("field_type") not in NUMERIC_UI_TYPES:
        raise _fail(key, f"aggregate '{aggregate}' requires a numeric field")
    compiled.setdefault("label", binding.get("field") or "Count")
    return compiled, referenced, readable_roles


def _json_safe(key: str, label: str, value: Any) -> None:
    try:
        json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise _fail(key, f"{label} must contain JSON-serializable values") from exc


def _compile_hierarchy_leaf(
    key: str,
    raw_leaf: Any,
    *,
    base_model: ModelDefinition,
    preset: dict[str, Any],
    lookup: dict[str, ModelDefinition],
) -> tuple[dict[str, Any], list[ModelDefinition], set[str]]:
    """Compile and validate an optional non-recursive hierarchy leaf model."""

    if preset["contract"] != "hierarchy":
        raise _fail(key, "leaf is only supported by hierarchy presets")
    if not isinstance(raw_leaf, dict):
        raise _fail(key, "leaf must be created with tree_leaf(...) or be a dictionary")

    leaf_name = raw_leaf.get("model")
    if isinstance(leaf_name, type):
        leaf_name = leaf_name.__name__
    leaf_model = lookup.get(str(leaf_name).lower())
    if leaf_model is None:
        raise _fail(key, f"leaf references unknown model '{leaf_name}'")
    if leaf_model is base_model:
        raise _fail(key, "leaf model must differ from the hierarchy model")

    raw_inputs = raw_leaf.get("inputs")
    if not isinstance(raw_inputs, dict):
        raise _fail(key, "leaf must define id, parent, and name inputs")
    required = {"id", "parent", "name"}
    if "value" in preset["required"]:
        required.add("value")
    unknown = set(raw_inputs) - {"id", "parent", "name", "value"}
    missing = required - set(raw_inputs)
    if unknown or missing:
        details = []
        if missing:
            details.append(f"is missing input(s): {', '.join(sorted(missing))}")
        if unknown:
            details.append(f"has unsupported input(s): {', '.join(sorted(unknown))}")
        raise _fail(key, f"leaf {'; '.join(details)}")

    compiled_inputs: dict[str, Any] = {}
    readable_roles = set(ROLE_ORDER)
    for name, binding in raw_inputs.items():
        compiled, refs, field_roles = _compile_binding(key, binding, leaf_model, lookup)
        if compiled["kind"] != "dimension":
            raise _fail(key, f"leaf input '{name}' must use dim(...)")
        if compiled.get("joins") or compiled.get("bucket") or compiled.get("extract"):
            raise _fail(key, f"leaf input '{name}' must be a direct model field")
        compiled_inputs[name] = compiled
        # Primary IDs are already part of every readable resource's identity;
        # introspection intentionally gives undeclared ID fields no field-level
        # permissions, so do not make hierarchy leaves unusable because of it.
        if name == "id" and compiled.get("field") == "id":
            field_roles = set(ROLE_ORDER)
        readable_roles &= field_roles
        if refs != [leaf_model]:  # Defensive: direct fields never reference another model.
            raise _fail(key, f"leaf input '{name}' must not traverse a relation")

    leaf_value = compiled_inputs.get("value")
    if leaf_value and leaf_value.get("field_type") not in NUMERIC_UI_TYPES:
        raise _fail(key, "leaf input 'value' must resolve to a numeric field")

    parent_field = compiled_inputs["parent"]["field"]
    fk = next(
        (item for item in leaf_model.get("foreign_keys", []) if item["name"] == parent_field),
        None,
    )
    if fk is None or str(fk["target_model"]).lower() != str(base_model["name"]).lower():
        raise _fail(
            key,
            f"leaf parent '{parent_field}' must be a direct foreign key from "
            f"{leaf_model['name']} to {base_model['name']}",
        )

    return ({
        "model": {
            "module": leaf_model["source_module"],
            "name": leaf_model["name"],
            "owner_field": leaf_model.get("owner_field"),
        },
        "inputs": compiled_inputs,
    }, [leaf_model], readable_roles)


def compile_visualizations(
    declarations: list[dict[str, Any]],
    models: list[ModelDefinition],
) -> list[dict[str, Any]]:
    """Validate declarations against introspected models and compile query metadata."""

    lookup = _model_lookup(models)
    seen: set[str] = set()
    compiled_specs: list[dict[str, Any]] = []

    for declaration in declarations:
        key = declaration.get("key")
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError("Visualization keys must be valid identifiers")
        if key in seen:
            raise _fail(key, "key is duplicated")
        seen.add(key)
        title = declaration.get("title")
        if not isinstance(title, str) or not title.strip():
            raise _fail(key, "title must be a non-empty string")
        preset_name = declaration.get("preset")
        preset = PRESETS.get(str(preset_name))
        if preset is None:
            raise _fail(key, f"unknown preset '{preset_name}'")
        model_name = declaration.get("model")
        if isinstance(model_name, type):
            model_name = model_name.__name__
        base_model = lookup.get(str(model_name).lower())
        if base_model is None:
            raise _fail(key, f"references unknown model '{model_name}'")

        inputs = declaration.get("inputs")
        if inputs is None:
            allowed_top_level = CONTRACT_INPUTS[preset["contract"]]
            inputs = {name: declaration[name] for name in allowed_top_level if name in declaration}
        if not isinstance(inputs, dict):
            raise _fail(key, "inputs must be an object")
        unknown_inputs = set(inputs) - CONTRACT_INPUTS[preset["contract"]]
        if unknown_inputs:
            raise _fail(key, f"preset '{preset_name}' does not accept input(s): {', '.join(sorted(unknown_inputs))}")
        missing = set(preset["required"]) - set(inputs)
        if missing:
            raise _fail(key, f"preset '{preset_name}' requires input(s): {', '.join(sorted(missing))}")

        compiled_inputs: dict[str, Any] = {}
        referenced_models: list[ModelDefinition] = [base_model]
        permitted_roles = set(ROLE_ORDER)
        for input_name, raw_binding in inputs.items():
            if isinstance(raw_binding, (list, tuple)):
                if input_name != "y" or preset["contract"] != "xy_series":
                    raise _fail(key, "only the y input of a multi-series chart may be a list")
                if len(raw_binding) < 2:
                    raise _fail(key, "a y input list must contain at least two metrics")
                compiled_list = []
                for item in raw_binding:
                    result, refs, field_roles = _compile_binding(key, item, base_model, lookup)
                    if result["kind"] != "metric":
                        raise _fail(key, "items in a y input list must be metrics")
                    compiled_list.append(result)
                    referenced_models.extend(ref for ref in refs if ref not in referenced_models)
                    permitted_roles &= field_roles
                compiled_inputs[input_name] = compiled_list
            else:
                result, refs, field_roles = _compile_binding(key, raw_binding, base_model, lookup)
                compiled_inputs[input_name] = result
                referenced_models.extend(ref for ref in refs if ref not in referenced_models)
                if (
                    preset["contract"] == "hierarchy"
                    and input_name == "id"
                    and result.get("field") == "id"
                ):
                    field_roles = set(ROLE_ORDER)
                permitted_roles &= field_roles

        if preset["contract"] == "xy_series" and "series" not in compiled_inputs and not isinstance(compiled_inputs.get("y"), list):
            raise _fail(key, "multi-series charts require series=dim(...) or a list of y metrics")
        if isinstance(compiled_inputs.get("y"), list) and "series" in compiled_inputs:
            raise _fail(key, "use either series=dim(...) or a list of y metrics, not both")
        if preset["renderer"] == "scatter":
            for axis in ("x", "y"):
                binding = compiled_inputs[axis]
                if isinstance(binding, list) or binding.get("field_type") not in NUMERIC_UI_TYPES:
                    raise _fail(key, f"scatter input '{axis}' must resolve to a numeric field")
        for numeric_slot in ({"y", "value", "max"} & set(compiled_inputs)):
            slot_bindings = compiled_inputs[numeric_slot]
            slot_bindings = slot_bindings if isinstance(slot_bindings, list) else [slot_bindings]
            for binding in slot_bindings:
                if binding.get("field_type") not in NUMERIC_UI_TYPES and binding.get("aggregate") not in {"count", "distinct_count"}:
                    raise _fail(key, f"input '{numeric_slot}' must produce numeric values")

        compiled_leaf = None
        if declaration.get("leaf") is not None:
            compiled_leaf, leaf_models, leaf_roles = _compile_hierarchy_leaf(
                key,
                declaration["leaf"],
                base_model=base_model,
                preset=preset,
                lookup=lookup,
            )
            referenced_models.extend(leaf_models)
            permitted_roles &= leaf_roles

        where = declaration.get("where") or {}
        if not isinstance(where, dict):
            raise _fail(key, "where must be an object")
        compiled_where = []
        for field_path, value in where.items():
            resolved, refs = _resolve_field_path(key, base_model, field_path, lookup)
            referenced_models.extend(ref for ref in refs if ref not in referenced_models)
            target_field = _find_field(refs[-1], resolved["field"])
            if target_field is not None:
                permitted_roles &= _field_readable_roles(target_field)
            if isinstance(value, dict):
                if set(value) != {"period"} or value["period"] not in RELATIVE_TIME_PERIODS:
                    supported = ", ".join(sorted(RELATIVE_TIME_PERIODS))
                    raise _fail(
                        key,
                        "relative time where conditions must be {'period': <period>}, "
                        f"where <period> is one of: {supported}",
                    )
                if target_field is None or target_field.get("ui_type") not in {"date", "datetime"}:
                    raise _fail(key, f"relative time where field '{field_path}' must be a date or datetime field")
            compiled_where.append({"binding": resolved, "value": value})

        raw_filters = declaration.get("filters") or []
        if not isinstance(raw_filters, (list, tuple)):
            raise _fail(key, "filters must be a list")
        compiled_filters = []
        filter_keys: set[str] = set()
        for raw_filter in raw_filters:
            if not isinstance(raw_filter, dict):
                raise _fail(key, "each filter must be an object")
            filter_key = raw_filter.get("key")
            field_path = raw_filter.get("field")
            filter_type = raw_filter.get("type", "select")
            if not isinstance(filter_key, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", filter_key):
                raise _fail(key, "filter keys must be valid identifiers")
            if filter_key in filter_keys:
                raise _fail(key, f"filter key '{filter_key}' is duplicated")
            if filter_type not in FILTER_TYPES:
                raise _fail(key, f"filter '{filter_key}' has unsupported type '{filter_type}'")
            filter_keys.add(filter_key)
            resolved, refs = _resolve_field_path(key, base_model, field_path, lookup)
            referenced_models.extend(ref for ref in refs if ref not in referenced_models)
            target_field = _find_field(refs[-1], resolved["field"])
            if target_field is not None:
                permitted_roles &= _field_readable_roles(target_field)
            compiled_filter = {
                "key": filter_key,
                "label": raw_filter.get("label", filter_key.replace("_", " ").title()),
                "type": filter_type,
                "binding": resolved,
            }
            if target_field is not None and target_field.get("is_enum"):
                target_model = refs[-1]
                compiled_filter["option_i18n_key"] = (
                    f"models.{target_model['module_name']}.enums.{target_field['name']}"
                )
            compiled_filters.append(compiled_filter)

        for model in referenced_models:
            permitted_roles &= {
                role for role in ROLE_ORDER
                if "r" in model.get("role_permissions", {}).get(role, "")
            }
        visible = declaration.get("visible")
        if visible is not None:
            if not isinstance(visible, (list, tuple)) or any(role not in ROLE_ORDER for role in visible):
                raise _fail(key, "visible must contain only user, admin, or developer")
            permitted_roles &= set(visible)
        if not permitted_roles:
            raise _fail(key, "is not readable by any role after permission intersection")

        limit = declaration.get("limit", 1000)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 5000:
            raise _fail(key, "limit must be an integer between 1 and 5000")
        order_by = declaration.get("order_by") or []
        if not isinstance(order_by, (list, tuple)):
            raise _fail(key, "order_by must be a list")
        for item in order_by:
            slot = str(item).removeprefix("-")
            if slot not in compiled_inputs:
                raise _fail(key, f"order_by references unknown input '{slot}'")

        placement = {"page": "dashboard", "span": 6, "order": 100, **(declaration.get("placement") or {})}
        if placement["page"] != "dashboard":
            raise _fail(key, "placement.page currently only supports 'dashboard'")
        if placement["span"] not in {4, 6, 8, 12}:
            raise _fail(key, "placement.span must be 4, 6, 8, or 12")
        options = declaration.get("options") or {}
        if not isinstance(options, dict):
            raise _fail(key, "options must be an object")
        forbidden_options = {"dataset", "series"} & set(options)
        if forbidden_options:
            raise _fail(key, f"options cannot override generated key(s): {', '.join(sorted(forbidden_options))}")
        _json_safe(key, "where", where)
        _json_safe(key, "placement", placement)
        _json_safe(key, "options", options)

        compiled_specs.append({
            "key": key,
            "title": title,
            "preset": preset_name,
            "renderer": preset["renderer"],
            "contract": preset["contract"],
            "model": {
                "module": base_model["source_module"],
                "name": base_model["name"],
                "owner_field": base_model.get("owner_field"),
            },
            "inputs": compiled_inputs,
            "where": compiled_where,
            "filters": compiled_filters,
            "order_by": list(order_by),
            "limit": limit,
            "permitted_roles": [role for role in ROLE_ORDER if role in permitted_roles],
            "placement": placement,
            "options": options,
            **({"leaf": compiled_leaf} if compiled_leaf is not None else {}),
        })

    return sorted(compiled_specs, key=lambda item: (item["placement"]["order"], item["key"]))


def compile_dashboard_metrics(
    declarations: list[dict[str, Any]],
    models: list[ModelDefinition],
) -> dict[str, list[dict[str, Any]]]:
    """Validate project-level KPI declarations and group them by source model.

    Metric evaluation remains model-scoped so the existing generated endpoint
    and permission model can be reused unchanged.  The normalizer is shared
    with the legacy ``__onesite__.dashboard_metrics`` configuration to keep
    both entry points behaviorally identical during the migration period.
    """

    # Import lazily to keep the model introspection module independent from
    # project-level declaration loading at import time.
    from .introspect import _normalize_dashboard_metrics

    lookup = _model_lookup(models)
    grouped_raw: dict[str, list[dict[str, Any]]] = {}
    for index, declaration in enumerate(declarations):
        metric = dict(declaration)
        model_name = metric.pop("model", None)
        if isinstance(model_name, type):
            model_name = model_name.__name__
        base_model = lookup.get(str(model_name).lower())
        key = metric.get("key", f"at index {index}")
        if base_model is None:
            raise ValueError(
                f"Dashboard metric '{key}' references unknown model '{model_name}'"
            )
        canonical_name = base_model["name"]
        grouped_raw.setdefault(canonical_name, []).append(metric)

    model_by_name = {model["name"]: model for model in models}
    return {
        model_name: _normalize_dashboard_metrics(
            raw_metrics,
            model_name=model_name,
            fields=model_by_name[model_name]["fields"],
            role_permissions=model_by_name[model_name]["role_permissions"],
        )
        for model_name, raw_metrics in grouped_raw.items()
    }


def apply_dashboard_metrics(
    models: list[ModelDefinition],
    project_metrics: dict[str, list[dict[str, Any]]],
) -> None:
    """Add compiled project-level KPIs to their model generation metadata."""

    for model in models:
        additions = project_metrics.get(model["name"], [])
        if not additions:
            continue
        existing = model.get("dashboard_metrics", [])
        existing_keys = {metric["key"] for metric in existing}
        duplicate_keys = existing_keys & {metric["key"] for metric in additions}
        if duplicate_keys:
            keys = ", ".join(sorted(duplicate_keys))
            raise ValueError(
                f"Model '{model['name']}': dashboard_metrics key(s) configured both "
                f"in __onesite__ and visualizations.py: {keys}"
            )
        model["dashboard_metrics"] = sorted(
            [*existing, *additions],
            key=lambda metric: (metric["order"], metric["key"]),
        )


def load_and_compile_visualizations(
    cwd: Path,
    models: list[ModelDefinition],
) -> list[dict[str, Any]]:
    return compile_visualizations(load_visualizations(cwd), models)


def load_and_compile_dashboard_metrics(
    cwd: Path,
    models: list[ModelDefinition],
) -> dict[str, list[dict[str, Any]]]:
    """Load, validate, and group project-level Dashboard KPI declarations."""

    return compile_dashboard_metrics(load_dashboard_metrics(cwd), models)


__all__ = [
    "PRESETS",
    "apply_dashboard_metrics",
    "compile_dashboard_metrics",
    "compile_visualizations",
    "load_and_compile_dashboard_metrics",
    "load_and_compile_visualizations",
    "load_dashboard_metrics",
    "load_visualizations",
]
