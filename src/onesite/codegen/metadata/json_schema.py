"""Structured JSON field schemas, nested layouts, and conditional field rules."""

import inspect
from datetime import date as date_type, datetime as datetime_type, time as time_type
from enum import Enum
from typing import Any, Dict, List, Set, get_args, get_origin

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from onesite.config import normalize_onesite_config

from ..naming import to_snake as _to_snake
from .fields import (
    _get_field_site_props,
    _get_numeric_bounds,
    _is_pydantic_model,
    _unwrap_optional,
)


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
