"""Phase 3 — Model introspection.

Imports the user's SQLModel classes and extracts field-level metadata
(fields, foreign keys, permissions, search configuration, etc.) into
:class:`~onesite.codegen.types.ModelDefinition` objects that drive
the downstream code generation phases.
"""

import importlib
import inspect
from pathlib import Path
from typing import Any

from pydantic_core import PydanticUndefined
import sqlmodel.main
from sqlmodel import SQLModel

from onesite.config import normalize_onesite_config
from onesite_runtime import ACTION_METADATA_ATTRIBUTE, ActionMetadata

from ..introspect import get_model_fields
from ..model_imports import ModelIntrospectionError, isolated_project_imports
from ..types import (
    FieldDefinition,
    ModelDefinition,
    ModelIntrospectResult,
)
from .base import console, to_snake


# ── SQLModel monkey-patch ────────────────────────────────────────────────


def _install_snake_case_tablenames() -> None:
    """Monkey-patch SQLModel to auto-generate snake_case table names."""
    if getattr(sqlmodel.main, "_onesite_snake_tablename_installed", False):
        return

    original_new = sqlmodel.main.SQLModelMetaclass.__new__

    def patched_new(mcls, name, bases, dict_, **kwargs):
        if kwargs.get("table", False) and "__tablename__" not in dict_:
            dict_["__tablename__"] = to_snake(name)
        return original_new(mcls, name, bases, dict_, **kwargs)

    sqlmodel.main.SQLModelMetaclass.__new__ = patched_new
    sqlmodel.main._onesite_snake_tablename_installed = True


# ── Password field helper ────────────────────────────────────────────────


def _ensure_user_password_field(fields: list[FieldDefinition]) -> None:
    """Append a default password field to the User model if it lacks one."""
    has_password = any(f["name"] == "password" for f in fields)
    if has_password:
        return

    fields.append(
        FieldDefinition(
            name="password",
            type="str",
            ui_type="str",
            permissions="cu",
            create_optional=False,
            update_optional=True,
            required=True,
            default=PydanticUndefined,
            is_search_field=False,
            fk_info=None,
            allow_download=True,
            label_key="models.user.fields.password",
            is_unique=False,
        )
    )


# ── Model metadata assembly ──────────────────────────────────────────────


def _normalize_ui_layout(
    raw_ui: Any,
    *,
    model_name: str,
    displayable_fields: list[str],
    view: str,
) -> list[dict[str, Any]]:
    """Validate and normalize a ``__onesite__[\"ui\"]`` form or detail layout.

    The caller supplies fields appropriate for the target view.  Detail
    layouts exclude relationship cards and JSON collection tabs because they
    have their own data loading and pagination behaviour; form layouts include
    editable model fields.

    The normalized form is consumed by the frontend template.  Doing this in
    the generator gives model authors useful errors for misspelled fields
    instead of silently producing an incomplete page.
    """
    if raw_ui is None:
        return []
    displayable_field_set = set(displayable_fields)
    if not isinstance(raw_ui, dict):
        raise ValueError(
            f"Invalid ui configuration for {model_name}: 'ui' must be an object."
        )

    raw_view = raw_ui.get(view)
    if raw_view is None:
        return []
    if not isinstance(raw_view, dict):
        raise ValueError(
            f"Invalid ui.{view} configuration for {model_name}: expected an object."
        )

    raw_layout = raw_view.get("layout")
    if not isinstance(raw_layout, list) or not raw_layout:
        raise ValueError(
            f"Invalid ui.{view}.layout configuration for {model_name}: "
            "expected a non-empty list."
        )

    def field_node(raw: Any, path: str) -> dict[str, Any]:
        if isinstance(raw, str):
            field_name, span = raw, 1
        elif isinstance(raw, dict) and set(raw).issubset({"field", "span"}):
            field_name = raw.get("field")
            span = raw.get("span", 1)
        else:
            raise ValueError(
                f"Invalid {path} for {model_name}: expected a field name or "
                "{'field': 'name', 'span': n}."
            )

        if not isinstance(field_name, str) or not field_name:
            raise ValueError(f"Invalid {path} for {model_name}: field must be a non-empty string.")
        if field_name not in displayable_field_set:
            available = ", ".join(displayable_fields) or "(none)"
            raise ValueError(
                f"Invalid {path} for {model_name}: field {field_name!r} cannot be "
                f"placed in ui.{view}.layout. Available fields: {available}."
            )
        if not isinstance(span, int) or isinstance(span, bool) or not 1 <= span <= 4:
            raise ValueError(f"Invalid {path} for {model_name}: span must be an integer from 1 to 4.")
        return {"kind": "field", "field": field_name, "span": span}

    def section_node(raw: dict[str, Any], path: str) -> dict[str, Any]:
        allowed = {"section", "title", "items", "span"}
        unknown = set(raw) - allowed
        if unknown:
            raise ValueError(
                f"Invalid {path} for {model_name}: unsupported keys {', '.join(sorted(unknown))}."
            )
        section = raw.get("section")
        title = raw.get("title")
        items = raw.get("items")
        span = raw.get("span", 1)
        if not isinstance(section, str) or not section:
            raise ValueError(f"Invalid {path} for {model_name}: section must be a non-empty string.")
        if not isinstance(title, str) or not title:
            raise ValueError(f"Invalid {path} for {model_name}: title must be a non-empty string.")
        if not isinstance(items, list) or not items:
            raise ValueError(f"Invalid {path} for {model_name}: items must be a non-empty list.")
        if not isinstance(span, int) or isinstance(span, bool) or not 1 <= span <= 4:
            raise ValueError(f"Invalid {path} for {model_name}: span must be an integer from 1 to 4.")
        return {
            "kind": "section",
            "section": section,
            "title": title,
            "span": span,
            "items": [row_node(item, f"{path}.items[{index}]") for index, item in enumerate(items)],
        }

    def row_node(raw: Any, path: str) -> dict[str, Any]:
        # A list is a horizontal row. A single field/section is normalized into
        # a one-cell row, making the grammar predictable at every nesting level.
        raw_cells = raw if isinstance(raw, list) else [raw]
        if not raw_cells:
            raise ValueError(f"Invalid {path} for {model_name}: a row cannot be empty.")
        cells: list[dict[str, Any]] = []
        for index, cell in enumerate(raw_cells):
            cell_path = f"{path}[{index}]" if isinstance(raw, list) else path
            if isinstance(cell, dict) and "section" in cell:
                cells.append(section_node(cell, cell_path))
            else:
                cells.append(field_node(cell, cell_path))
        total_span = sum(cell["span"] for cell in cells)
        if total_span > 4:
            raise ValueError(
                f"Invalid {path} for {model_name}: a row may use at most 4 columns, got {total_span}."
            )
        return {"kind": "row", "columns": total_span, "items": cells}

    layout = [row_node(item, f"ui.{view}.layout[{index}]") for index, item in enumerate(raw_layout)]

    seen_fields: set[str] = set()

    def collect_fields(node: dict[str, Any]) -> None:
        if node["kind"] == "field":
            field_name = node["field"]
            if field_name in seen_fields:
                raise ValueError(
                    f"Invalid ui.{view}.layout for {model_name}: field {field_name!r} is configured more than once."
                )
            seen_fields.add(field_name)
        else:
            for child in node["items"]:
                collect_fields(child)

    for node in layout:
        collect_fields(node)

    # Preserve existing behaviour for fields omitted from a custom layout by
    # appending them as a final one-column row.
    for field_name in displayable_fields:
        if field_name in seen_fields:
            continue
        layout.append({"kind": "row", "columns": 1, "items": [{"kind": "field", "field": field_name, "span": 1}]})
    return layout


def _form_layout_from_detail_layout(
    detail_layout: list[dict[str, Any]], form_fields: list[str]
) -> list[dict[str, Any]]:
    """Reuse the detail layout for forms, omitting read-only fields.

    Keeping one declarative layout avoids divergent detail and editor UIs.
    Fields that are writable but cannot appear in the detail layout (such as a
    password) are appended in declaration order.
    """
    allowed = set(form_fields)
    seen: set[str] = set()

    def filter_node(node: dict[str, Any]) -> dict[str, Any] | None:
        if node["kind"] == "field":
            if node["field"] not in allowed:
                return None
            seen.add(node["field"])
            return node
        items = [child for item in node["items"] if (child := filter_node(item)) is not None]
        if not items:
            return None
        if node["kind"] == "row":
            return {**node, "columns": sum(item["span"] for item in items), "items": items}
        return {**node, "items": items}

    layout = [node for item in detail_layout if (node := filter_node(item)) is not None]
    for field_name in form_fields:
        if field_name not in seen:
            layout.append({"kind": "row", "columns": 1, "items": [{"kind": "field", "field": field_name, "span": 1}]})
    return layout


def _build_model_dict(
    name: str,
    module_name: str,
    source_module: str,
    result: ModelIntrospectResult,
    *,
    table_name: str | None = None,
) -> ModelDefinition:
    """Assemble the canonical model metadata from introspection results.

    Returns a :class:`ModelDefinition` (dict subclass) that holds all
    model-level metadata consumed by the Jinja2 templates and later
    pipeline phases.
    """
    schema_imports = sorted({imp for f in result.fields for imp in f.py_imports})
    table_name = table_name or to_snake(name)
    # ``id`` is conventionally the primary key.  Keep its resolved type in
    # model metadata so generated schemas, routes and frontend clients also
    # work for business keys such as ``id: str``.
    id_field = next((field for field in result.fields if field.name == "id"), None)
    id_type = id_field.type if id_field is not None else "int"
    # SQLModel models commonly declare generated IDs as ``Optional[int]``.
    # The database response and path parameter are still concrete values.
    if id_type.startswith("Optional[") and id_type.endswith("]"):
        id_type = id_type[len("Optional["):-1]

    # Object-like JSON arrays behave more like inline related records on the
    # detail page than scalar fields.  Keep scalar date/time arrays in the
    # basic-information form, where their dedicated editor remains useful.
    json_array_fields = [
        field
        for field in result.fields
        if field.ui_type == "json"
        and field.json_kind == "array"
        and not field.json_item_kind
        and "r" in field.permissions
    ]
    json_dict_fields = [
        field
        for field in result.fields
        if field.ui_type == "json"
        and field.json_kind == "object"
        and field.type.startswith("Dict[")
        and "r" in field.permissions
    ]
    json_tab_names = {field.name for field in json_array_fields + json_dict_fields}
    displayable_fields = [
        field.name
        for field in result.fields
        if not field.fk_info and field.name not in json_tab_names and "r" in field.permissions
    ]
    detail_layout = _normalize_ui_layout(
        result.model_site_props.get("ui"),
        model_name=name,
        displayable_fields=displayable_fields,
        view="detail",
    )
    form_fields = [
        field.name
        for field in result.fields
        if "c" in field.permissions or "u" in field.permissions
    ]
    form_layout = _form_layout_from_detail_layout(detail_layout, form_fields)

    # ── Tree view detection ──────────────────────────────────────────────
    tree_view_config = result.model_site_props.get("tree_view", "auto")
    is_tree = False
    tree_parent_field = None

    if tree_view_config is not False:
        for fk in result.foreign_keys:
            if fk.is_self_referencing:
                tree_parent_field = fk.name
                if tree_view_config is True or tree_view_config == "auto":
                    is_tree = True
                break

    return ModelDefinition(
        name=name,
        module_name=module_name,
        source_module=source_module,
        lower_name=name.lower(),
        table_name=table_name,
        fields=result.fields,
        detail_layout=detail_layout,
        form_layout=form_layout,
        json_array_fields=json_array_fields,
        json_dict_fields=json_dict_fields,
        id_type=id_type,
        schema_imports=schema_imports,
        foreign_keys=result.foreign_keys,
        search_field=result.search_field,
        unique_search_field=result.unique_search_field,
        is_link_table=result.is_link_table,
        is_singleton=result.is_singleton,
        model_permissions=result.model_permissions,
        role_permissions=result.role_permissions,
        role_visible=result.role_visible,
        frontend_only=result.frontend_only,
        translations=result.model_translations,
        refresh_interval=result.refresh_interval,
        reverse_fk_display=result.reverse_fk_display,
        site_props=result.model_site_props,
        actions=result.actions,
        is_notification_table=result.is_notification_table,
        union_key=result.union_key,
        importable=result.importable,
        exportable=result.exportable,
        import_key=result.import_key,
        visualize=result.model_site_props.get("visualize"),
        dashboard_metrics=result.model_site_props.get("dashboard_metrics", []),
        data_reports=result.model_site_props.get("data_reports", []),
        has_created_at=any(f.name == "created_at" for f in result.fields),
        owner_field=result.owner_field,
        page_edit=result.page_edit,
        edit_mode=result.edit_mode,
        standalone=bool(result.model_site_props.get("standalone", True)),
        is_timescaledb=result.is_timescaledb,
        is_latest_table=result.model_site_props.get("is_latest_table", False),
        timescaledb_entity_field=result.timescaledb_entity_field,
        timescaledb_metric_field=result.timescaledb_metric_field,
        timescaledb_time_field=result.timescaledb_time_field,
        timescaledb_model_table=result.timescaledb_model_table,
        property_config=result.property_config,
        is_tree=is_tree,
        tree_parent_field=tree_parent_field,
        icon=result.model_site_props.get("icon", "LayoutDashboard"),
    )


# ── Event listener extraction ───────────────────────────────────────────


_TRANSACTIONAL_HOOK_ARGUMENTS = {
    "on_before_create": {"self", "session", "context"},
    "on_after_create": {"self", "session", "context"},
    "on_before_update": {"self", "session", "old", "changes", "context"},
    "on_after_update": {"self", "session", "old", "changes", "context"},
    "on_before_delete": {"self", "session", "old", "context"},
    "on_after_delete": {"self", "session", "old", "context"},
    "on_after_commit_create": {"self", "context"},
    "on_after_commit_update": {"self", "old", "changes", "context"},
    "on_after_commit_delete": {"self", "old", "context"},
}
_BULK_DELETE_HOOK_ARGUMENTS = {
    "on_after_bulk_delete": {"cls", "session", "olds", "context"},
    "on_after_commit_bulk_delete": {"cls", "olds", "context"},
}
_REMOVED_MODEL_HOOKS = {
    "on_background_after_create",
    "on_background_after_update",
    "on_background_after_delete",
    "on_orm_before_insert",
    "on_orm_after_insert",
    "on_orm_before_update",
    "on_orm_after_update",
    "on_orm_before_delete",
    "on_orm_after_delete",
    "on_before_insert",
    "on_after_insert",
}


def _validate_named_hook_signature(
    model_cls: type,
    hook_name: str,
    method: Any,
    supported: set[str],
) -> None:
    """Fail generation when a hook cannot be invoked with its documented API."""
    signature = inspect.signature(method)
    for parameter in signature.parameters.values():
        if parameter.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        if parameter.kind is inspect.Parameter.POSITIONAL_ONLY:
            raise ValueError(
                f"{model_cls.__name__}.{hook_name} parameter "
                f"'{parameter.name}' cannot be positional-only"
            )
        if parameter.name not in supported and parameter.default is inspect.Parameter.empty:
            expected = ", ".join(sorted(supported - {"self"}))
            raise ValueError(
                f"{model_cls.__name__}.{hook_name} has unsupported required "
                f"parameter '{parameter.name}'. Supported parameters: {expected}"
            )


def _validate_service_hooks(model_cls: type) -> None:
    """Validate supported hooks and reject retired hook families."""
    for hook_name, supported in _TRANSACTIONAL_HOOK_ARGUMENTS.items():
        method = inspect.getattr_static(model_cls, hook_name, None)
        if method is None:
            continue
        if isinstance(method, (classmethod, staticmethod)) or not inspect.isfunction(method):
            raise ValueError(
                f"{model_cls.__name__}.{hook_name} must be an instance method"
            )
        _validate_named_hook_signature(model_cls, hook_name, method, supported)

    for hook_name, supported in _BULK_DELETE_HOOK_ARGUMENTS.items():
        method = inspect.getattr_static(model_cls, hook_name, None)
        if method is None:
            continue
        if not isinstance(method, classmethod):
            raise ValueError(
                f"{model_cls.__name__}.{hook_name} must be a classmethod"
            )
        _validate_named_hook_signature(
            model_cls, hook_name, method.__func__, supported
        )

    for hook_name in sorted(_REMOVED_MODEL_HOOKS):
        method = inspect.getattr_static(model_cls, hook_name, None)
        if method is None:
            continue
        raise ValueError(
            f"{model_cls.__name__}.{hook_name} is no longer supported. "
            "Use on_after_create/update/delete for transactional work or "
            "on_after_commit_create/update/delete for post-commit work."
        )


_ACTION_ARGUMENTS = {"self", "context", "session", "current_user"}


def _validate_action_method_signature(
    model_cls: type,
    method_name: str,
    method: Any,
) -> None:
    """Validate the dependency names supported by generated action dispatch."""

    signature = inspect.signature(method)
    parameters = list(signature.parameters.values())
    if not parameters or parameters[0].name != "self":
        raise ValueError(
            f"{model_cls.__name__}.{method_name} must be an instance method "
            "whose first parameter is 'self'"
        )
    _validate_named_hook_signature(
        model_cls,
        method_name,
        method,
        _ACTION_ARGUMENTS,
    )


def _extract_function_actions(model_cls: type) -> dict[str, dict[str, Any]]:
    """Extract methods decorated with :func:`onesite_runtime.action`."""

    actions: dict[str, dict[str, Any]] = {}
    for method_name, raw_method in vars(model_cls).items():
        if isinstance(raw_method, (classmethod, staticmethod)):
            decorated = getattr(raw_method.__func__, ACTION_METADATA_ATTRIBUTE, None)
            if decorated is not None:
                raise ValueError(
                    f"{model_cls.__name__}.{method_name} must be an instance method"
                )
            continue
        metadata = getattr(raw_method, ACTION_METADATA_ATTRIBUTE, None)
        if metadata is None:
            continue
        if not isinstance(metadata, ActionMetadata) or not inspect.isfunction(raw_method):
            raise ValueError(
                f"Invalid action metadata on {model_cls.__name__}.{method_name}"
            )
        _validate_action_method_signature(model_cls, method_name, raw_method)

        availability_handler = metadata.availability_handler
        if metadata.condition is not None and availability_handler is not None:
            raise ValueError(
                f"{model_cls.__name__}.{method_name} cannot define both "
                "condition= and @action.available"
            )
        if availability_handler is not None:
            guard = inspect.getattr_static(model_cls, availability_handler, None)
            if isinstance(guard, (classmethod, staticmethod)) or not inspect.isfunction(guard):
                raise ValueError(
                    f"Availability handler {model_cls.__name__}.{availability_handler} "
                    "must be an instance method"
                )
            _validate_action_method_signature(model_cls, availability_handler, guard)

        actions[method_name] = {
            "function": True,
            "handler": method_name,
            "permissions": metadata.permissions,
            "label": metadata.label,
            "unavailable": metadata.unavailable,
            "condition": metadata.condition,
            "availability_handler": availability_handler,
            "dynamic_availability": availability_handler is not None,
        }
    return actions


# ── Module-level introspection ───────────────────────────────────────────


def _process_introspected_class(
    obj: type, name: str, module_name: str
) -> ModelDefinition | None:
    """Run ``get_model_fields`` on a single class and build its metadata dict."""
    model_module_name = to_snake(name)
    result = get_model_fields(obj, model_module_name)
    _validate_service_hooks(obj)
    function_actions = _extract_function_actions(obj)
    duplicate_actions = sorted(set(result.actions) & set(function_actions))
    if duplicate_actions:
        duplicates = ", ".join(duplicate_actions)
        raise ValueError(
            f"{name} defines action(s) in both __onesite__ and decorated "
            f"methods: {duplicates}"
        )
    result.actions.update(function_actions)

    if name == "User":
        _ensure_user_password_field(result.fields)

    # Standard CSV imports need an import_key for upsert.  Custom import
    # handlers receive the uploaded file directly and own their persistence.
    import_config = result.model_site_props.get("importable", False)
    is_custom_import = isinstance(import_config, dict) and import_config.get("custom") is True
    if result.importable and not is_custom_import:
        if result.import_key:
            pass  # use configured key
        elif any(f["name"] == "title" and f.get("is_unique") for f in result.fields):
            result.import_key = "title"
        else:
            console.print(
                f"[red]Error: Model '{name}' has importable=True but no import_key configured.[/red]"
            )
            console.print(
                "[red]Please set __onesite__ = {'import_key': 'field_name'} "
                "or ensure 'title' field has unique=True[/red]"
            )
            return None

    mdl = _build_model_dict(
        name,
        module_name,
        module_name,
        result,
        table_name=getattr(obj, "__tablename__", None),
    )

    table = getattr(obj, "__table__", None)
    mdl["primary_key_columns"] = (
        [str(column.name) for column in table.primary_key.columns]
        if table is not None
        else []
    )

    mdl["has_function_actions"] = any(
        action_config.get("function", False)
        for action_config in result.actions.values()
        if isinstance(action_config, dict)
    )
    mdl["has_dynamic_action_states"] = any(
        action_config.get("dynamic_availability", False)
        for action_config in result.actions.values()
        if isinstance(action_config, dict)
    )

    return mdl


def _introspect_module(
    module: Any, module_name: str
) -> list[ModelDefinition] | None:
    """Introspect a single model module and return model metadata dicts."""
    results: list[ModelDefinition] = []

    for name, obj in inspect.getmembers(module):
        if not (inspect.isclass(obj) and issubclass(obj, SQLModel) and obj is not SQLModel):
            continue

        table_args = getattr(obj, "__table_args__", None)
        singleton_marker = False
        if isinstance(table_args, dict):
            info = table_args.get("info", {})
            site_props = info.get("site_props", {})
            singleton_marker = bool(site_props.get("is_singleton", False))

        onesite_props = normalize_onesite_config(getattr(obj, "__onesite__", None))
        onesite_marker = False
        if onesite_props is not None:
            onesite_marker = bool(
                onesite_props.get("frontend_only")
                or onesite_props.get("is_singleton")
            )

        # Built-in model auto-detection (SystemConfig → singleton, CustomConfig → frontend_only)
        builtin_marker = name in ("SystemConfig", "CustomConfig")

        if not (hasattr(obj, "metadata") and (getattr(obj, "__table__", None) is not None or singleton_marker or onesite_marker or builtin_marker)):
            continue

        mdl = _process_introspected_class(obj, name, module_name)
        if mdl is None:
            return None  # fatal — caller should stop
        results.append(mdl)

    return results


# ── Public entry point ───────────────────────────────────────────────────


def phase_introspect(backend_path: Path) -> list[ModelDefinition]:
    """Import every SQLModel module and extract field-level metadata.

    Returns an empty list only when the project contains no models. Import and
    validation failures raise :class:`ModelIntrospectionError`.
    """
    _install_snake_case_tablenames()

    with isolated_project_imports(backend_path):
        try:
            importlib.import_module("app.models")
        except Exception as exc:
            raise ModelIntrospectionError(
                f"Could not import generated model package app.models: {exc}"
            ) from exc

        models_dir = backend_path / "app" / "models"
        module_names = sorted(
            model_file.stem
            for model_file in models_dir.glob("*.py")
            if model_file.stem != "__init__" and not model_file.stem.startswith("_")
        )
        found_models: list[ModelDefinition] = []

        for module_name in module_names:
            full_module_name = f"app.models.{module_name}"
            try:
                module = importlib.import_module(full_module_name)
            except Exception as exc:
                raise ModelIntrospectionError(
                    f"Could not import generated model module {full_module_name}: {exc}"
                ) from exc

            module_models = _introspect_module(module, module_name)
            if module_models is None:
                raise ModelIntrospectionError(
                    f"Model validation failed while introspecting {full_module_name}"
                )
            found_models.extend(module_models)

        return found_models
