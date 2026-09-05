"""Validation and normalization of selectable model display configuration."""

from typing import Any

from ..types import FieldDefinition


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
