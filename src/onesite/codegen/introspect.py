import inspect
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic_core import PydanticUndefined
from rich.console import Console
from sqlmodel import SQLModel

console = Console()

def _to_snake(name: str) -> str:
    import re

    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


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
    if inspect.isclass(annotation) and issubclass(annotation, BaseModel) and not issubclass(annotation, SQLModel):
        return "model"
    origin = get_origin(annotation)
    if origin is list or annotation is list:
        return "array"
    return "any"


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
        ann = f.annotation
        kind = _json_field_kind_from_annotation(ann)
        field_schema: Dict[str, Any] = {"name": fname, "kind": kind}
        if kind == "enum" and inspect.isclass(ann) and issubclass(ann, Enum):
            field_schema["enumValues"] = [e.value for e in ann]
        elif kind == "model" and inspect.isclass(ann) and issubclass(ann, BaseModel) and not issubclass(ann, SQLModel):
            field_schema["model"] = _build_json_model_schema(ann, visited=visited, depth=depth + 1)
        elif kind == "array":
            origin = get_origin(ann)
            args = get_args(ann) if origin is list else ()
            item_ann = args[0] if args else Any
            item_kind = _json_field_kind_from_annotation(item_ann)
            item_schema: Dict[str, Any] = {"kind": item_kind}
            if item_kind == "enum" and inspect.isclass(item_ann) and issubclass(item_ann, Enum):
                item_schema["enumValues"] = [e.value for e in item_ann]
            elif item_kind == "model" and inspect.isclass(item_ann) and issubclass(item_ann, BaseModel) and not issubclass(item_ann, SQLModel):
                item_schema["model"] = _build_json_model_schema(item_ann, visited=visited, depth=depth + 1)
            field_schema["item"] = item_schema
        fields.append(field_schema)
    return {"name": model.__name__, "fields": fields}


def get_model_fields(
    model_cls: type[SQLModel], module_name: str | None = None
) -> Tuple[
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    str,
    bool,
    bool,
    str,
    bool,
    Dict[str, Any],
    bool,
    int,
    bool,
    Dict[str, Any],
    Dict[str, Any],
    bool,
    Optional[List[str]],
    bool,
    bool,
]:
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
    model_permissions = model_site_props.get("permissions", "admin")
    frontend_only = model_site_props.get("frontend_only", False)
    model_translations = model_site_props.get("translations", {})
    auto_refresh = model_site_props.get("auto_refresh", False)
    refresh_interval = model_site_props.get("refresh_interval", 5000)
    reverse_fk_display = model_site_props.get("reverse_fk_display", True)
    actions = model_site_props.get("actions", {})
    is_notification_table = bool(model_site_props.get("is_notification_table", False))
    union_key = model_site_props.get("union_key", None)
    importable = model_site_props.get("importable", False)
    exportable = model_site_props.get("exportable", False)
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

        permissions = site_props.get("permissions", "rcu")
        create_optional = site_props.get("create_optional", False)
        update_optional = site_props.get("update_optional", False)
        allow_download = site_props.get("allow_download", True)

        if name == "id":
            permissions = "r"

        console.print(f"Debug: Field {name} - Perms: {permissions}")

        type_annotation = field.annotation
        type_str = str(type_annotation)

        console.print(
            f"Debug: Field {name} - Type Annotation: {type_annotation} (Type: {type(type_annotation)}) - Type Str: {type_str}"
        )

        is_enum = False
        enum_values: List[Any] = []
        json_kind = None
        json_py_imports: List[str] = []
        json_model_schema = None
        json_item_schema = None

        if inspect.isclass(type_annotation) and issubclass(type_annotation, (str, int)) and hasattr(type_annotation, "__members__"):
            is_enum = True
            enum_values = [e.value for e in type_annotation]
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
                if inspect.isclass(item_type) and issubclass(item_type, BaseModel) and not issubclass(item_type, SQLModel):
                    type_str = f"List[{item_type.__name__}]"
                    json_py_imports.append(item_type.__name__)
                    json_item_schema = _build_json_model_schema(item_type)
                elif item_type in (dict,) or item_origin is dict:
                    value_type = item_args[1] if len(item_args) >= 2 else Any
                    if inspect.isclass(value_type) and issubclass(value_type, BaseModel) and not issubclass(value_type, SQLModel):
                        type_str = f"List[Dict[str, {value_type.__name__}]]"
                        json_py_imports.append(value_type.__name__)
                    else:
                        type_str = "List[Dict[str, Any]]"
                else:
                    type_str = "List[Any]"
            else:
                json_kind = "object"
                value_type = args[1] if len(args) >= 2 else Any
                if inspect.isclass(value_type) and issubclass(value_type, BaseModel) and not issubclass(value_type, SQLModel):
                    type_str = f"Dict[str, {value_type.__name__}]"
                    json_py_imports.append(value_type.__name__)
                else:
                    type_str = "Dict[str, Any]"
        elif inspect.isclass(resolved_annotation) and issubclass(resolved_annotation, BaseModel) and not issubclass(resolved_annotation, SQLModel):
            json_kind = "object"
            type_str = resolved_annotation.__name__
            json_py_imports.append(resolved_annotation.__name__)
            json_model_schema = _build_json_model_schema(resolved_annotation)
        else:
            # Check for time type first - must check before datetime since datetime.time contains "datetime"
            # The type_str is like "<class 'datetime.time'>" for time type
            # We need to check for 'datetime.time' specifically to not match datetime.datetime
            if "'datetime.time'" in type_str:
                type_str = "time"
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

        if site_props.get("component") == "image":
            ui_type = "image"
        elif site_props.get("component") == "file":
            ui_type = "file"
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

        fk_info = None
        if name.endswith("_id") and name != "id":
            is_fk = False
            if hasattr(field, "foreign_key") and field.foreign_key is not PydanticUndefined and field.foreign_key is not None:
                is_fk = True
            if site_props.get("is_foreign_key"):
                is_fk = True
            if is_fk:
                fk_table = name[:-3]
                if hasattr(field, "foreign_key") and field.foreign_key and isinstance(field.foreign_key, str):
                    fk_table = field.foreign_key.split(".")[0]

                target_model_class = "".join(word.capitalize() for word in fk_table.split("_"))
                target_service = site_props.get("target_service") or _to_snake(target_model_class)
                target_endpoint = f"{target_service}s"

                reverse_display = site_props.get("reverse_display", True)
                fk_info = {
                    "name": name,
                    "target_model": target_model_class,
                    "target_service": target_service,
                    "target_endpoint": target_endpoint,
                    "label_field": "name",
                    "reverse_display": reverse_display,
                }

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

        default_value = None if field.default is PydanticUndefined else field.default
        if is_enum and default_value is not None and hasattr(default_value, "value"):
            default_value = default_value.value

        fields.append(
            {
                "name": name,
                "type": type_str,
                "ui_type": ui_type,
                "json_kind": json_kind,
                "json_model_schema": json_model_schema,
                "json_item_schema": json_item_schema,
                "py_imports": sorted(set(json_py_imports)),
                "permissions": permissions,
                "create_optional": create_optional,
                "update_optional": update_optional,
                "required": field.is_required(),
                "default": default_value,
                "default_factory": (
                    "list"
                    if getattr(field, "default_factory", None) is list
                    else "dict"
                    if getattr(field, "default_factory", None) is dict
                    else None
                ),
                "is_enum": is_enum,
                "enum_values": enum_values,
                "is_search_field": is_search_field,
                "fk_info": fk_info,
                "allow_download": allow_download,
                "label_key": label_key,
                "translations": translations,
                "is_unique": is_unique,
                "is_local_storage": is_local_storage,
            }
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

    return (
        fields,
        foreign_keys,
        search_field,
        is_link_table,
        is_singleton,
        model_permissions,
        frontend_only,
        model_translations,
        auto_refresh,
        refresh_interval,
        reverse_fk_display,
        model_site_props,
        actions,
        is_notification_table,
        union_key,
        importable,
        exportable,
    )
