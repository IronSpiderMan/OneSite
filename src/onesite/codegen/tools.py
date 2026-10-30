"""Compile class-based tools into serializable generation metadata."""

from __future__ import annotations

import inspect
import keyword
from enum import Enum
from typing import Any, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field

from onesite_runtime.tools import (
    BaseTool,
    ExecutionOptions,
    InputFile,
    OutputFile,
    ResultUI,
    Role,
    ToolTranslation,
)

from .metadata.fields import _get_field_site_props, _unwrap_optional


class ExecutableMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    execution: ExecutionOptions
    result_ui: ResultUI
    translations: dict[str, ToolTranslation]


class _ToolMetadata(ExecutableMetadata):
    permissions: list[Role] = Field(min_length=1)


def _translations(model: type[BaseModel]) -> dict[str, Any]:
    config = getattr(model, "__onesite__", {})
    if isinstance(config, BaseModel):
        config = config.model_dump(exclude_unset=True)
    result = dict(config.get("translations", {})) if isinstance(config, dict) else {}
    legacy = getattr(model, "__i18n__", {})
    if isinstance(legacy, dict):
        result.update(legacy)
    return result


def _resolve(schema: dict, document: dict, seen: tuple[str, ...] = ()) -> dict:
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref in seen or not ref.startswith("#/$defs/"):
            raise ValueError(f"Recursive/external tool schemas are unsupported: {ref}")
        target = document["$defs"][
            ref.removeprefix("#/$defs/").replace("~1", "/").replace("~0", "~")
        ]
        return _resolve(
            {**target, **{k: v for k, v in schema.items() if k != "$ref"}}, document, (*seen, ref)
        )
    return schema


def _fields(model: type[BaseModel], *, mode: str = "validation") -> list[dict[str, Any]]:
    document = model.model_json_schema(mode=mode)
    if document.get("type") != "object":
        raise ValueError(f"{model.__name__}: tool models must describe an object")

    def field_node(name: str, raw: dict, required: bool, seen: tuple[str, ...] = ()) -> dict:
        ref = raw.get("$ref")
        schema = _resolve(raw, document, seen)
        next_seen = (*seen, ref) if ref else seen
        nullable = False
        if "anyOf" in schema:
            choices = [part for part in schema["anyOf"] if part.get("type") != "null"]
            nullable = len(choices) != len(schema["anyOf"])
            if len(choices) != 1:
                raise ValueError(f"{model.__name__}.{name}: only nullable unions are supported")
            schema = {
                **_resolve(choices[0], document, next_seen),
                **{key: value for key, value in schema.items() if key != "anyOf"},
            }
            if choices[0].get("$ref"):
                next_seen = (*next_seen, choices[0]["$ref"])
        kind = schema.get("type")
        props = schema.get("site_props", {})
        node: dict[str, Any] = {
            "name": name,
            "label": schema.get("title", name.replace("_", " ").title()),
            "required": required,
            "nullable": nullable or kind == "null" or None in schema.get("enum", []),
            "help": schema.get("description", ""),
            "schema_type": kind,
        }
        for source, target in (
            ("default", "default"),
            ("minimum", "min"),
            ("maximum", "max"),
            ("minLength", "min_length"),
            ("maxLength", "max_length"),
            ("pattern", "pattern"),
            ("minItems", "min_items"),
            ("maxItems", "max_items"),
        ):
            if source in schema:
                node[target] = schema[source]
        if "enum" in schema or "const" in schema:
            options = [
                item for item in schema.get("enum", [schema.get("const")]) if item is not None
            ]
            node.update(type="select" if options else "json", options=options)
        elif kind in ("integer", "number"):
            node.update(type="number", number_kind="int" if kind == "integer" else "float")
        elif kind == "boolean":
            node["type"] = "bool"
        elif kind == "string":
            node["type"] = {"date": "date", "date-time": "datetime"}.get(
                schema.get("format"), "str"
            )
        elif kind == "object":
            node["type"] = "json"
            if "properties" in schema:
                node["fields"] = [
                    field_node(key, value, key in schema.get("required", []), next_seen)
                    for key, value in schema["properties"].items()
                ]
        elif kind == "array":
            item = field_node("item", schema.get("items", {}), False, next_seen)
            if item["type"] == "select":
                node.update(type="multi_select", options=item["options"])
            else:
                node.update(type="json", item=item)
        elif kind in (None, "null") and not any(key in schema for key in ("oneOf", "allOf")):
            node["type"] = "json"
        else:
            raise ValueError(f"{model.__name__}.{name}: unsupported field schema {schema}")
        component = props.get("component")
        if component in ("textarea", "text") and node["type"] == "str":
            node["type"] = "text"
        if component == "json":
            node.pop("fields", None)
            node.pop("item", None)
        for key in ("placeholder", "accept", "max_size_mb"):
            if key in props:
                node[key] = props[key]
        return node

    nodes = [
        field_node(name, schema, name in document.get("required", []))
        for name, schema in document.get("properties", {}).items()
    ]
    _decorate_fields(nodes, model, mode=mode)
    return nodes


def _decorate_fields(nodes: list[dict], model: type[BaseModel], *, mode: str) -> None:
    translations = _translations(model)
    for name, field in model.model_fields.items():
        alias = (
            (field.serialization_alias if mode == "serialization" else field.validation_alias)
            or field.alias
            or name
        )
        node = next((item for item in nodes if item["name"] == alias), None)
        if node is None:
            continue
        annotation, _ = _unwrap_optional(field.annotation)
        if get_origin(annotation) is list:
            annotation, _ = _unwrap_optional(next(iter(get_args(annotation)), Any))
            nested = node.get("item", {})
        else:
            nested = node
        if (
            inspect.isclass(annotation)
            and issubclass(annotation, BaseModel)
            and nested.get("fields")
        ):
            _decorate_fields(nested["fields"], annotation, mode=mode)
        enum_translations = (
            getattr(annotation, "__i18n__", {})
            if inspect.isclass(annotation) and issubclass(annotation, Enum)
            else {}
        )
        for language, options in enum_translations.items():
            node.setdefault("translations", {}).setdefault(language, {})["options"] = options
        for language, pack in translations.items():
            if not isinstance(pack, dict):
                raise ValueError(f"{model.__name__}.__i18n__.{language} must be an object")
            text = pack.get("fields", pack).get(name)
            if isinstance(text, str):
                text = {"label": text}
            if isinstance(text, dict):
                node.setdefault("translations", {}).setdefault(language, {}).update(
                    {"label" if k == "title" else k: v for k, v in text.items()}
                )
            options = pack.get("enums", {}).get(name)
            if options:
                node.setdefault("translations", {}).setdefault(language, {})["options"] = options


def _contains_file(annotation: Any, seen: tuple[type, ...] = ()) -> bool:
    if inspect.isclass(annotation) and issubclass(annotation, InputFile):
        return True
    if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
        if annotation in seen:
            return False
        return any(
            _contains_file(field.annotation, (*seen, annotation))
            for field in annotation.model_fields.values()
        )
    return any(_contains_file(arg, seen) for arg in get_args(annotation))


def _validate_models(annotation: Any, prefix: str, seen: tuple[type, ...] = ()) -> None:
    if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
        if annotation in seen:
            return
        if getattr(annotation, "__pydantic_root_model__", False):
            raise ValueError(f"{prefix}: RootModel is unsupported; use an object model")
        for name, field in annotation.model_fields.items():
            if field.validation_alias is not None and not isinstance(field.validation_alias, str):
                raise ValueError(f"{prefix}.{name}: use string field aliases")
            _validate_models(field.annotation, f"{prefix}.{name}", (*seen, annotation))
    else:
        for argument in get_args(annotation):
            _validate_models(argument, prefix, seen)


def declaration_metadata(
    declaration: type,
    metadata_model: type[ExecutableMetadata],
    *,
    namespace: str,
    label: str,
) -> dict[str, Any]:
    """Validate the common class declaration and preserve an import binding."""
    prefix = f"{label} {declaration.__name__}"
    if inspect.isabstract(declaration):
        raise ValueError(f"{prefix}: implement async run(inputs, context)")
    if (
        not declaration.__module__.startswith(f"app.{namespace}.")
        or declaration.__qualname__ != declaration.__name__
    ):
        raise ValueError(f"{prefix}: declare a top-level class in app/{namespace}/*.py")
    if not inspect.iscoroutinefunction(declaration.run):
        raise ValueError(f"{prefix}.run must be async")
    try:
        inspect.signature(declaration).bind()
        inspect.signature(declaration.run).bind(None, inputs=None, context=None)
    except TypeError as exc:
        raise ValueError(
            f"{prefix}: use a no-argument constructor and run(self, inputs, context): {exc}"
        ) from exc
    metadata = metadata_model(
        **{name: getattr(declaration, name, None) for name in metadata_model.model_fields}
    ).model_dump(mode="json", exclude_none=True)
    name = metadata["name"]
    if not name.isidentifier() or keyword.iskeyword(name) or name == "__init__":
        raise ValueError(f"{prefix}.name must be a valid Python identifier")
    if not metadata["title"].strip():
        raise ValueError(f"{prefix}.title must not be blank")
    return {
        **metadata,
        "handler": name,
        "class_path": f"{declaration.__module__}:{declaration.__name__}",
    }


def compile_models(
    tool: type, ui: dict, *, prefix: str, allow_uploads: bool = True
) -> dict[str, Any]:
    """Compile input/output contracts shared by tools and scheduled tasks."""
    for key in ("inputs", "result"):
        model = getattr(tool, key, None)
        if not inspect.isclass(model) or not issubclass(model, BaseModel):
            raise ValueError(f"{prefix}.{key} must be a Pydantic model class")
        _validate_models(model, f"{prefix}.{key}")
    inputs = _fields(tool.inputs)
    for name, field in tool.inputs.model_fields.items():
        alias = field.validation_alias or field.alias or name
        if alias == "__inputs__":
            raise ValueError(f"{prefix}.inputs: __inputs__ is reserved for the form payload")
        node = next(item for item in inputs if item["name"] == alias)
        annotation, _ = _unwrap_optional(field.annotation)
        multiple = get_origin(annotation) is list
        item, _ = (
            _unwrap_optional(next(iter(get_args(annotation)), Any))
            if multiple
            else (annotation, False)
        )
        if inspect.isclass(item) and issubclass(item, InputFile):
            if not allow_uploads:
                raise ValueError(
                    f"{prefix}.inputs.{name}: scheduled tasks use durable resource IDs instead of InputFile uploads"
                )
            props = _get_field_site_props(field)
            node.pop("fields", None)
            node.pop("item", None)
            node.update(
                type="files" if multiple else "file", max_size_mb=props.get("max_size_mb", 20)
            )
            node["max_files"] = node.get("max_items", 10)
            node["history_name"] = field.serialization_alias or field.alias or name
        elif _contains_file(field.annotation):
            raise ValueError(
                f"{prefix}.inputs.{name}: file uploads must be top-level InputFile fields"
            )
    if _contains_file(tool.result):
        raise ValueError(f"{prefix}.result: use OutputFile for results, not InputFile")
    fields = _fields(tool.result, mode="serialization")
    selected = next((node for node in fields if node["name"] == ui.get("field")), None)
    if ui["renderer"] in ("text", "table", "download"):
        if selected is None:
            raise ValueError(f"{prefix}.result_ui.field must name a result field")
        if ui["renderer"] == "table" and not selected.get("item", {}).get("fields"):
            raise ValueError(
                f"{prefix}.result_ui.field must be an array of objects for table rendering"
            )
        if ui["renderer"] == "text" and selected.get("schema_type") != "string":
            raise ValueError(f"{prefix}.result_ui.field must be a string for text rendering")
        if ui["renderer"] == "download":
            field = next(
                (
                    field
                    for name, field in tool.result.model_fields.items()
                    if (field.serialization_alias or field.alias or name) == ui["field"]
                ),
                None,
            )
            if field is None or _unwrap_optional(field.annotation)[0] is not OutputFile:
                raise ValueError(
                    f"{prefix}.result_ui.field must be an OutputFile for download rendering"
                )
    return {
        "inputs": inputs,
        "input_schema": tool.inputs.model_json_schema(),
        "result_schema": tool.result.model_json_schema(mode="serialization"),
        "result": {"type": "json", "fields": fields},
    }


def compile_tool(tool: type[BaseTool]) -> dict[str, Any]:
    metadata = declaration_metadata(tool, _ToolMetadata, namespace="tools", label="Tool")
    return {
        **metadata,
        **compile_models(tool, metadata["result_ui"], prefix=f"Tool {tool.__name__}"),
    }
