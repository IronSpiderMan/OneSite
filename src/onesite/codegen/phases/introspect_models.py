"""Phase 3 — Model introspection.

Imports the user's SQLModel classes and extracts field-level metadata
(fields, foreign keys, permissions, search configuration, etc.) into
:class:`~onesite.codegen.types.ModelDefinition` objects that drive
the downstream code generation phases.
"""

import importlib
import inspect
import sys
import textwrap
import asyncio
from pathlib import Path
from typing import Any

from pydantic_core import PydanticUndefined
import sqlmodel.main
from sqlmodel import SQLModel

from ..introspect import get_model_fields
from ..types import (
    EventListener,
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


def _build_model_dict(
    name: str,
    module_name: str,
    source_module: str,
    result: ModelIntrospectResult,
) -> ModelDefinition:
    """Assemble the canonical model metadata from introspection results.

    Returns a :class:`ModelDefinition` (dict subclass) that holds all
    model-level metadata consumed by the Jinja2 templates and later
    pipeline phases.
    """
    schema_imports = sorted({imp for f in result.fields for imp in f.py_imports})
    table_name = to_snake(name)

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
        has_created_at=any(f.name == "created_at" for f in result.fields),
        owner_field=result.owner_field,
        page_edit=result.page_edit,
        is_timescaledb=result.is_timescaledb,
        is_latest_table=result.model_site_props.get("is_latest_table", False),
        timescaledb_entity_field=result.timescaledb_entity_field,
        timescaledb_metric_field=result.timescaledb_metric_field,
        timescaledb_model_table=result.timescaledb_model_table,
        property_config=result.property_config,
        is_tree=is_tree,
        tree_parent_field=tree_parent_field,
        icon=result.model_site_props.get("icon", "LayoutDashboard"),
    )


# ── Event listener extraction ───────────────────────────────────────────


def _extract_event_listeners(model_cls: type) -> list[EventListener]:
    """Extract ``on_before_*`` / ``on_after_*`` methods as event listeners.

    Scans the model class for methods whose names match the pattern
    ``on_(before|after)_<event>``, extracts their source code bodies,
    and returns ``EventListener`` objects for code generation.

    The ``self`` parameter is stripped from the generated function —
    the template adds ``self = target`` so existing ``self.`` references
    in the body still work.
    """
    listeners: list[EventListener] = []
    for name, method in inspect.getmembers(model_cls, predicate=inspect.isfunction):
        if not (name.startswith("on_before_") or name.startswith("on_after_")):
            continue

        event_name = name[3:]  # strip "on_" prefix → "before_insert", etc.
        try:
            source = inspect.getsource(method)
        except (OSError, TypeError):
            continue

        lines = source.splitlines()
        # Skip decorator / def / async def lines to reach the body
        body_start = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("def ") or stripped.startswith("async def "):
                body_start = i + 1
                break
        body_lines = lines[body_start:]
        if not body_lines:
            continue

        is_async = asyncio.iscoroutinefunction(method)

        has_session_param = False
        has_old_param = False
        if is_async:
            try:
                sig = inspect.signature(method)
                has_session_param = "session" in sig.parameters
                has_old_param = "old" in sig.parameters
            except (ValueError, TypeError):
                pass
        else:
            try:
                sig = inspect.signature(method)
                has_old_param = "old" in sig.parameters
            except (ValueError, TypeError):
                pass

        body = textwrap.dedent("\n".join(body_lines))
        # Remove surrounding blank lines
        body = body.strip("\n")
        listeners.append(
            EventListener(
                event_name=event_name,
                body=body,
                is_async=is_async,
                has_session_param=has_session_param,
                has_old_param=has_old_param,
            )
        )

    return listeners


# ── Module-level introspection ───────────────────────────────────────────


def _process_introspected_class(
    obj: type, name: str, module_name: str, full_module_name: str
) -> ModelDefinition | None:
    """Run ``get_model_fields`` on a single class and build its metadata dict."""
    model_module_name = to_snake(name)
    result = get_model_fields(obj, model_module_name)

    if name == "User":
        _ensure_user_password_field(result.fields)

    # Validate importable models have an import_key
    if result.importable:
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
        name, module_name, module_name, result,
    )

    # Attach event listeners (extracted from on_before_* / on_after_* methods)
    mdl["event_listeners"] = _extract_event_listeners(obj)

    return mdl


def _introspect_module(
    module: Any, module_name: str, full_module_name: str
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

        onesite_props = getattr(obj, "__onesite__", None)
        onesite_marker = False
        if isinstance(onesite_props, dict):
            onesite_marker = bool(
                onesite_props.get("frontend_only")
                or onesite_props.get("is_singleton")
            )

        # Built-in model auto-detection (SystemConfig → singleton, CustomConfig → frontend_only)
        builtin_marker = name in ("SystemConfig", "CustomConfig")

        if not (hasattr(obj, "metadata") and (getattr(obj, "__table__", None) is not None or singleton_marker or onesite_marker or builtin_marker)):
            continue

        mdl = _process_introspected_class(obj, name, module_name, full_module_name)
        if mdl is None:
            return None  # fatal — caller should stop
        results.append(mdl)

    return results


# ── Public entry point ───────────────────────────────────────────────────


def phase_introspect(backend_path: Path) -> list[ModelDefinition]:
    """Import every SQLModel module and extract field-level metadata.

    Returns a list of model metadata dicts, or an empty list on critical failure.
    """
    _install_snake_case_tablenames()
    sys.path.insert(0, str(backend_path))

    try:
        import app.models  # noqa: F401
    except ImportError as e:
        console.print(f"[red]Could not import app.models: {e}[/red]")
        return []

    models_dir = backend_path / "app" / "models"
    module_names = [
        f.stem for f in models_dir.glob("*.py")
        if f.stem != "__init__" and not f.stem.startswith("_")
    ]
    found_models: list[ModelDefinition] = []

    for module_name in module_names:
        full_module_name = f"app.models.{module_name}"
        try:
            if full_module_name in sys.modules:
                module = sys.modules[full_module_name]
            else:
                module = importlib.import_module(full_module_name)
        except ImportError as e:
            console.print(f"[red]Error importing {full_module_name}: {e}[/red]")
            continue

        module_models = _introspect_module(module, module_name, full_module_name)
        if module_models is None:  # fatal error (e.g. missing import_key)
            return []
        found_models.extend(module_models)

    return found_models
