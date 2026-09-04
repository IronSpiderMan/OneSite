import inspect
import re
from types import UnionType
from datetime import date as date_type, datetime as datetime_type, time as time_type
from enum import Enum
from typing import Any, Dict, List, Set, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic_core import PydanticUndefined
from rich.console import Console
from sqlmodel import SQLModel

from onesite.config import normalize_onesite_config

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


def _unwrap_optional(annotation: Any) -> tuple[Any, bool]:
    """Return the value type inside ``Optional[T]``/``T | None``.

    ``typing.Optional`` and the PEP 604 ``| None`` syntax have different
    origins at runtime.  Treating only ``typing.Union`` as optional caused
    otherwise typed JSON fields to fall through to the string fallback.
    """
    if get_origin(annotation) in (Union, UnionType):
        value_types = [item for item in get_args(annotation) if item is not type(None)]
        if len(value_types) == 1 and len(value_types) != len(get_args(annotation)):
            return value_types[0], True
    return annotation, False


def _json_field_kind_from_annotation(annotation: Any) -> str:
    annotation, _ = _unwrap_optional(annotation)
    if annotation is bool:
        return "bool"
    if annotation is int:
        return "int"
    if annotation is float:
        return "float"
    if annotation is str:
        return "str"
    if annotation is datetime_type:
        return "datetime"
    if annotation is date_type:
        return "date"
    if annotation is time_type:
        return "time"
    if inspect.isclass(annotation) and issubclass(annotation, Enum):
        return "enum"
    if inspect.isclass(annotation) and _is_pydantic_model(annotation):
        return "model"
    origin = get_origin(annotation)
    if origin is list or annotation is list:
        return "array"
    if origin is dict or annotation is dict:
        return "object"
    return "any"


def _get_numeric_bounds(field: Any) -> tuple[Any, Any]:
    """Extract inclusive Pydantic ``ge``/``le`` constraints from FieldInfo."""
    minimum = maximum = None
    for constraint in getattr(field, "metadata", ()) or ():
        if getattr(constraint, "ge", None) is not None:
            minimum = constraint.ge
        if getattr(constraint, "le", None) is not None:
            maximum = constraint.le
    return minimum, maximum


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
        if controller.startswith("$root.") and not controller[6:]:
            raise ValueError(
                f"{model_name}.{field_name} site_props.{rule_name} root references "
                "must use $root.<field>"
            )
        values = expected if isinstance(expected, (list, tuple, set)) else [expected]
        if not values or any(isinstance(item, (dict, list, tuple, set)) for item in values):
            raise ValueError(
                f"{model_name}.{field_name} site_props.{rule_name}.{controller} "
                "must be a scalar or a non-empty list of scalars"
            )
        normalized[controller] = list(values)
    return normalized


def _get_json_model_ui(model: type[BaseModel]) -> Dict[str, Any]:
    """Return optional OneSite UI configuration declared by a JSON submodel."""
    for attribute in ("__onesite__", "__site_props__"):
        value = normalize_onesite_config(getattr(model, attribute, None))
        if value is not None:
            ui = value.get("ui")
            if isinstance(ui, dict):
                return ui
    return {}


def _get_json_model_i18n(model: type[BaseModel]) -> Dict[str, Any]:
    """Return field translations declared by a structured JSON submodel."""
    merged: Dict[str, Any] = {}
    config = normalize_onesite_config(getattr(model, "__onesite__", None))
    if isinstance(config, dict) and isinstance(config.get("translations"), dict):
        merged.update(config["translations"])
    legacy = getattr(model, "__i18n__", None)
    if isinstance(legacy, dict):
        merged.update(legacy)
    return merged


def _normalize_json_model_layout(
    raw_ui: Dict[str, Any], *, model_name: str, field_names: List[str], view: str
) -> List[Dict[str, Any]]:
    """Validate a Pydantic/SQLModel JSON submodel layout.

    The grammar deliberately matches the shared top-level detail layout so
    structured JSON fields use the same rows, spans, and titled sections in
    both detail and edit views.
    """
    raw_view = raw_ui.get(view)
    if raw_view is None:
        return []
    if not isinstance(raw_view, dict):
        raise ValueError(f"Invalid ui.{view} configuration for {model_name}: expected an object.")
    raw_layout = raw_view.get("layout")
    if not isinstance(raw_layout, list) or not raw_layout:
        raise ValueError(f"Invalid ui.{view}.layout configuration for {model_name}: expected a non-empty list.")

    available = set(field_names)

    def field_node(raw: Any, path: str) -> Dict[str, Any]:
        if isinstance(raw, str):
            name, span = raw, 1
        elif isinstance(raw, dict) and set(raw).issubset({"field", "span"}):
            name, span = raw.get("field"), raw.get("span", 1)
        else:
            raise ValueError(f"Invalid {path} for {model_name}: expected a field name or {{'field': 'name', 'span': n}}.")
        if not isinstance(name, str) or not name:
            raise ValueError(f"Invalid {path} for {model_name}: field must be a non-empty string.")
        if name not in available:
            raise ValueError(f"Invalid {path} for {model_name}: field {name!r} cannot be placed in ui.{view}.layout.")
        if not isinstance(span, int) or isinstance(span, bool) or not 1 <= span <= 4:
            raise ValueError(f"Invalid {path} for {model_name}: span must be an integer from 1 to 4.")
        return {"kind": "field", "field": name, "span": span}

    def section_node(raw: Dict[str, Any], path: str) -> Dict[str, Any]:
        if set(raw) - {"section", "title", "items", "span"}:
            raise ValueError(f"Invalid {path} for {model_name}: unsupported section keys.")
        section, title, items, span = raw.get("section"), raw.get("title"), raw.get("items"), raw.get("span", 1)
        if not isinstance(section, str) or not section or not isinstance(title, str) or not title:
            raise ValueError(f"Invalid {path} for {model_name}: section and title must be non-empty strings.")
        if not isinstance(items, list) or not items:
            raise ValueError(f"Invalid {path} for {model_name}: items must be a non-empty list.")
        if not isinstance(span, int) or isinstance(span, bool) or not 1 <= span <= 4:
            raise ValueError(f"Invalid {path} for {model_name}: span must be an integer from 1 to 4.")
        return {"kind": "section", "section": section, "title": title, "span": span,
                "items": [row_node(item, f"{path}.items[{index}]") for index, item in enumerate(items)]}

    def row_node(raw: Any, path: str) -> Dict[str, Any]:
        cells = raw if isinstance(raw, list) else [raw]
        if not cells:
            raise ValueError(f"Invalid {path} for {model_name}: a row cannot be empty.")
        items = [section_node(cell, f"{path}[{index}]") if isinstance(cell, dict) and "section" in cell else field_node(cell, f"{path}[{index}]") for index, cell in enumerate(cells)]
        columns = sum(item["span"] for item in items)
        if columns > 4:
            raise ValueError(f"Invalid {path} for {model_name}: a row may use at most 4 columns, got {columns}.")
        return {"kind": "row", "columns": columns, "items": items}

    layout = [row_node(item, f"ui.{view}.layout[{index}]") for index, item in enumerate(raw_layout)]
    seen: Set[str] = set()

    def collect(node: Dict[str, Any]) -> None:
        if node["kind"] == "field":
            if node["field"] in seen:
                raise ValueError(f"Invalid ui.{view}.layout for {model_name}: field {node['field']!r} is configured more than once.")
            seen.add(node["field"])
        else:
            for child in node["items"]:
                collect(child)

    for node in layout:
        collect(node)
    for name in field_names:
        if name not in seen:
            layout.append({"kind": "row", "columns": 1, "items": [{"kind": "field", "field": name, "span": 1}]})
    return layout


def _build_json_model_schema(
    model: type[BaseModel], visited: Set[type] | None = None, depth: int = 0
) -> Dict[str, Any]:
    if visited is None:
        visited = set()
    if model in visited or depth >= 2:
        return {"name": model.__name__, "fields": []}
    visited.add(model)
    fields: List[Dict[str, Any]] = []
    model_key = _to_snake(model.__name__)
    model_i18n = _get_json_model_i18n(model)
    for fname, f in model.model_fields.items():
        if fname == "property_key" or fname.startswith("_"):
            continue
        ann, nullable = _unwrap_optional(f.annotation)
        kind = _json_field_kind_from_annotation(ann)
        field_schema: Dict[str, Any] = {
            "name": fname,
            "kind": kind,
            "labelKey": f"json_models.{model_key}.fields.{fname}",
            "required": f.is_required(),
            "nullable": nullable,
        }
        minimum, maximum = _get_numeric_bounds(f)
        if minimum is not None:
            field_schema["minimum"] = minimum
        if maximum is not None:
            field_schema["maximum"] = maximum
        field_translations: Dict[str, str] = {}
        for language, pack in model_i18n.items():
            if not isinstance(pack, dict):
                continue
            fields_pack = pack.get("fields") if isinstance(pack.get("fields"), dict) else pack
            label = fields_pack.get(fname)
            if isinstance(label, str) and label:
                field_translations[language] = label
        if field_translations:
            field_schema["translations"] = field_translations
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
            item_ann, item_nullable = _unwrap_optional(args[0] if args else Any)
            item_kind = _json_field_kind_from_annotation(item_ann)
            item_schema: Dict[str, Any] = {"kind": item_kind, "nullable": item_nullable}
            if item_kind == "enum" and inspect.isclass(item_ann) and issubclass(item_ann, Enum):
                item_schema["enumValues"] = [e.value for e in item_ann]
            elif item_kind == "model" and inspect.isclass(item_ann) and _is_pydantic_model(item_ann):
                item_schema["model"] = _build_json_model_schema(item_ann, visited=visited, depth=depth + 1)
            field_schema["item"] = item_schema
        fields.append(field_schema)
    schema: Dict[str, Any] = {"name": model.__name__, "fields": fields}
    field_names = [field["name"] for field in fields]
    raw_ui = _get_json_model_ui(model)
    layout = _normalize_json_model_layout(
        raw_ui, model_name=model.__name__, field_names=field_names, view="detail"
    )
    if layout:
        schema["layout"] = layout
    return schema


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


def _json_schema_root_controllers(schema: Dict[str, Any] | None) -> Set[str]:
    """Collect top-level model fields referenced by ``$root.<field>`` rules."""
    controllers: Set[str] = set()
    if not schema:
        return controllers
    for field in schema.get("fields", []):
        for rule_name in ("visibleWhen", "requiredWhen"):
            for controller in (field.get(rule_name) or {}):
                if controller.startswith("$root."):
                    controllers.add(controller[6:].split(".", 1)[0])
        controllers.update(_json_schema_root_controllers(field.get("model")))
        item = field.get("item")
        if isinstance(item, dict):
            controllers.update(_json_schema_root_controllers(item.get("model")))
    return controllers


# ═══════════════════════════════════════════════════════════════════════════
# Three-layer permission system
# ═══════════════════════════════════════════════════════════════════════════

ROLE_ORDER = ["user", "admin", "developer"]
ROLE_LEVELS = {"user": 0, "admin": 1, "developer": 2}

DASHBOARD_METRIC_AGGREGATIONS = {
    "count", "sum", "avg", "min", "max", "distinct_count",
}
DASHBOARD_METRIC_PERIODS = {*RELATIVE_TIME_PERIODS, "all"}

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

TRACK_CRUD_OPERATIONS = {
    "c": "create",
    "r": "read",
    "u": "update",
    "d": "delete",
}
TRACK_EXTENDED_OPERATIONS = {"bulk_delete", "import", "export"}


def _normalize_tracked_operations(raw: Any, *, model_name: str) -> list[str]:
    """Validate ``site_props.track`` and return stable operation names."""
    if raw in (None, False, ""):
        return []

    tokens: list[str]
    if isinstance(raw, str):
        if any(char not in TRACK_CRUD_OPERATIONS for char in raw):
            raise ValueError(
                f"Model '{model_name}': track string must contain only c, r, u, d"
            )
        tokens = list(raw)
    elif isinstance(raw, list):
        tokens = raw
    else:
        raise ValueError(
            f"Model '{model_name}': track must be a CRUD string or a list"
        )

    operations: set[str] = set()
    for token in tokens:
        if token == "crud":
            operations.update(TRACK_CRUD_OPERATIONS.values())
        elif token in TRACK_CRUD_OPERATIONS:
            operations.add(TRACK_CRUD_OPERATIONS[token])
        elif token in TRACK_EXTENDED_OPERATIONS:
            operations.add(token)
        else:
            supported = "crud, c, r, u, d, bulk_delete, import, export"
            raise ValueError(
                f"Model '{model_name}': unsupported track operation {token!r}; "
                f"use one of: {supported}"
            )

    order = ("create", "read", "update", "delete", "bulk_delete", "import", "export")
    return [operation for operation in order if operation in operations]


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
        # String format: "admin-crud", "crud", "rcud"
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


def _normalize_multi_display(
    raw: Any,
    *,
    model_name: str,
    fields: list[FieldDefinition],
    default_label_field: str,
) -> dict[str, Any] | None:
    """Validate and enrich the model's selectable multi-item display config."""
    if raw is None or raw is False:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"{model_name}.multi_display must be an object")
    if raw.get("enabled", True) is False:
        return None

    raw_fields = raw.get("fields")
    if not isinstance(raw_fields, list) or not raw_fields:
        raise ValueError(f"{model_name}.multi_display.fields must be a non-empty list")

    field_by_name = {field.name: field for field in fields}
    inferred_renderers = {
        "image": "image",
        "images": "gallery",
        "video_stream": "video",
        "location": "map",
    }
    renderer_ui_types = {
        "image": {"image"},
        "gallery": {"images"},
        "video": {"video_stream"},
        "map": {"location"},
    }
    allowed_renderers = {"auto", "image", "gallery", "video", "map", "text"}
    normalized_fields: list[dict[str, Any]] = []
    seen_fields: set[str] = set()

    for entry in raw_fields:
        if isinstance(entry, str):
            config: dict[str, Any] = {"field": entry}
        elif isinstance(entry, dict):
            config = dict(entry)
        else:
            raise ValueError(
                f"{model_name}.multi_display.fields entries must be field names or objects"
            )

        field_name = config.get("field")
        if not isinstance(field_name, str) or not field_name:
            raise ValueError(
                f"{model_name}.multi_display field config requires a non-empty 'field'"
            )
        if field_name in seen_fields:
            raise ValueError(
                f"{model_name}.multi_display.fields contains duplicate field {field_name!r}"
            )
        field = field_by_name.get(field_name)
        if field is None:
            raise ValueError(
                f"{model_name}.multi_display references unknown field {field_name!r}"
            )
        if "r" not in field.permissions:
            raise ValueError(
                f"{model_name}.multi_display field {field_name!r} is not readable"
            )

        renderer = config.get("renderer", "auto")
        if renderer not in allowed_renderers:
            raise ValueError(
                f"{model_name}.multi_display field {field_name!r} has invalid renderer "
                f"{renderer!r}"
            )
        if renderer == "auto":
            renderer = inferred_renderers.get(field.ui_type, "text")
        compatible_ui_types = renderer_ui_types.get(renderer)
        if compatible_ui_types is not None and field.ui_type not in compatible_ui_types:
            raise ValueError(
                f"{model_name}.multi_display field {field_name!r} cannot use renderer "
                f"{renderer!r} with ui_type {field.ui_type!r}"
            )

        span = config.get("span", 4)
        zoom = config.get("zoom", 15)
        fit = config.get("fit", "contain")
        if not isinstance(span, int) or isinstance(span, bool) or not 1 <= span <= 4:
            raise ValueError(
                f"{model_name}.multi_display field {field_name!r} span must be between 1 and 4"
            )
        if not isinstance(zoom, int) or isinstance(zoom, bool) or not 1 <= zoom <= 18:
            raise ValueError(
                f"{model_name}.multi_display field {field_name!r} zoom must be between 1 and 18"
            )
        if fit not in {"cover", "contain"}:
            raise ValueError(
                f"{model_name}.multi_display field {field_name!r} fit must be 'cover' or 'contain'"
            )

        normalized_fields.append(
            {
                "field": field_name,
                "renderer": renderer,
                "span": span,
                "fit": fit,
                "zoom": zoom,
                "label_key": field.label_key,
                "ui_type": field.ui_type,
                "json_model_schema": field.json_model_schema,
                "json_item_schema": field.json_item_schema,
                "is_enum": field.is_enum,
                "is_multi_select": field.is_multi_select,
                "is_foreign_key": field.fk_info is not None,
                "stream_protocol": field.stream_protocol,
                "stream_autoplay": field.stream_autoplay,
                "stream_muted": field.stream_muted,
                "stream_controls": field.stream_controls,
                "stream_reconnect": field.stream_reconnect,
            }
        )
        seen_fields.add(field_name)

    label_field = raw.get("label_field") or default_label_field
    label_definition = field_by_name.get(label_field)
    if label_definition is None:
        raise ValueError(
            f"{model_name}.multi_display label_field {label_field!r} does not exist"
        )
    if "r" not in label_definition.permissions:
        raise ValueError(
            f"{model_name}.multi_display label_field {label_field!r} is not readable"
        )

    default_view = raw.get("default_view", "list")
    max_selected = raw.get("max_selected", 4)
    columns = raw.get("columns", 2)
    if default_view not in {"list", "multi"}:
        raise ValueError(
            f"{model_name}.multi_display.default_view must be 'list' or 'multi'"
        )
    if (
        not isinstance(max_selected, int)
        or isinstance(max_selected, bool)
        or not 1 <= max_selected <= 9
    ):
        raise ValueError(
            f"{model_name}.multi_display.max_selected must be between 1 and 9"
        )
    if not isinstance(columns, int) or isinstance(columns, bool) or not 1 <= columns <= 4:
        raise ValueError(
            f"{model_name}.multi_display.columns must be between 1 and 4"
        )

    return {
        "enabled": True,
        "fields": normalized_fields,
        "label_field": label_field,
        "default_view": default_view,
        "max_selected": max_selected,
        "columns": columns,
    }


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
