"""Phases 6 & 7 — Code generation.

Phase 6  — Per-model generation: schemas, CRUDs, services, API endpoints,
           frontend services, stores, pages, and backend tests.

Phase 7 — Aggregated / cross-cutting generation: API router, route tables,
          menu, dashboard, settings, profile, i18n locale files, WebSocket
          scaffolding, task pages, and feature flags.
"""

import json
import re
from pathlib import Path
from typing import Any

from ...project_paths import get_project_paths
from ..file_utils import copy_file_with_status
from ..custom_backend import sync_custom_backend
from ..i18n import generate_locale_files
from ..render import generate_file, generate_file_if_missing, generate_theme_file
from ..theme import resolve_theme
from ..router import update_api_router
from ..types import ModelDefinition
from .base import console


# ═══════════════════════════════════════════════════════════════════════════
# Visualize Filter Path Resolution
# ═══════════════════════════════════════════════════════════════════════════


def _quote_col(ref: str) -> str:
    """Quote the table name in a 'table.column' reference for use in text().

    e.g. 'group.id' -> '"group".id', 'alarm_record.rule_id' -> 'alarm_record.rule_id'
    """
    parts = ref.split(".", 1)
    if len(parts) == 2:
        return f'"{parts[0]}".{parts[1]}'
    return ref


def _quote_ddl_identifier(identifier: str) -> str:
    """Quote a SQLite/PostgreSQL identifier used in generated DDL."""
    return f'"{identifier.replace(chr(34), chr(34) * 2)}"'


def _render_create_index_sql(
    name: str,
    table: str,
    columns: list[str],
) -> str:
    """Render portable index DDL, including optional ASC/DESC modifiers."""
    rendered_columns: list[str] = []
    for column in columns:
        column_name, separator, order = column.rpartition(" ")
        if separator and order.upper() in {"ASC", "DESC"}:
            rendered_columns.append(
                f"{_quote_ddl_identifier(column_name)} {order.upper()}"
            )
        else:
            rendered_columns.append(_quote_ddl_identifier(column))
    return (
        f"CREATE INDEX IF NOT EXISTS {_quote_ddl_identifier(name)} "
        f"ON {_quote_ddl_identifier(table)} ({', '.join(rendered_columns)})"
    )


def _build_model_lookup(models: list[ModelDefinition]) -> dict[str, ModelDefinition]:
    """Build a dict mapping model names and table names to ModelDefinitions."""
    lookup: dict[str, ModelDefinition] = {}
    for m in models:
        lookup[m["name"]] = m
        lookup[m["table_name"]] = m
    return lookup


def _field_names(model: ModelDefinition) -> set[str]:
    return {str(field["name"]) for field in model.get("fields", [])}


def _normalize_external_resource(
    model: ModelDefinition,
    raw: Any,
) -> dict[str, str] | None:
    """Normalize one model-to-provider resource mapping.

    A provider represents one external system and may own many resource kinds.
    Each resource kind maps to exactly one OneSite model. The historical
    ``resource_type`` and ``identity_field`` names remain accepted as aliases.
    """
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"{model['name']} external_resource must be an object")

    provider = raw.get("provider")
    resource = raw.get("resource", raw.get("resource_type", model["module_name"]))
    identity_field = raw.get("identity", raw.get("identity_field", "id"))
    for key, value in (("provider", provider), ("resource", resource)):
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]+", value):
            raise ValueError(
                f"{model['name']} external_resource.{key} is required and "
                "may only contain letters, numbers, '.', '_', ':', or '-'"
            )
    if not isinstance(identity_field, str) or identity_field not in _field_names(model):
        raise ValueError(
            f"{model['name']} external_resource.identity references unknown field "
            f"'{identity_field}'"
        )
    return {
        "provider": provider,
        "resource": resource,
        "identity_field": identity_field,
    }


def _resolve_visualize_filters(
    model: ModelDefinition,
    model_lookup: dict[str, ModelDefinition],
) -> None:
    """Resolve filter paths into concrete join info for code generation.

    For each filter in model.visualize["filters"], traverses the FK chain
    defined by "path" and builds:
      - resolved_joins: list of (from_table, from_col, to_table, to_col)
      - resolved_options: join info for the filter options query

    Writes back to model.visualize["resolved_filters"].
    """
    viz = model.get("visualize")
    if not viz or not viz.get("filters"):
        return

    source_table = model["table_name"]
    resolved_filters = []

    for flt in viz["filters"]:
        # ── Enum (non-FK) filter: field directly on source model ──
        if flt.get("type") == "enum":
            field_name = flt["field"]
            field_def = next((f for f in model["fields"] if f["name"] == field_name), None)
            if not field_def:
                console.print(f"[yellow]Warning: Field '{field_name}' not found on model '{model['name']}', skipping filter[/yellow]")
                continue
            if not field_def.get("is_enum"):
                console.print(f"[yellow]Warning: Field '{field_name}' is not an enum field, skipping filter[/yellow]")
                continue
            resolved = {
                "name": flt.get("i18n_key", field_name),
                "filter_key": field_name,
                "filter_field": field_name,
                "filter_type": "enum",
                "enum_values": field_def["enum_values"],
                "filter_table": source_table,
                "fk_table": source_table,
                "fk_col": _quote_col(f"{source_table}.{field_name}"),
                "owner_model_class": model["name"],
                "owner_source_module": model["source_module"],
                "joins": [],
                "new_joins": [],
            }
            resolved_filters.append(resolved)
            continue

        # ── FK-based filter (existing logic) ──
        path = flt.get("path", "")
        filter_field = flt["filter_field"]
        filter_model_name = flt["model"]
        filter_label_field = flt.get("label_field", "title")

        filter_model = model_lookup.get(filter_model_name)
        if not filter_model:
            console.print(f"[yellow]Warning: Filter model '{filter_model_name}' not found, skipping filter[/yellow]")
            continue

        filter_table = filter_model["table_name"]
        segments = [s for s in path.split(".") if s] if path else []

        # Walk the FK chain and resolve each join step
        joins = []
        prev_table = source_table
        current_model = model

        for seg in segments:
            target_model = model_lookup.get(seg)
            if not target_model:
                console.print(f"[yellow]Warning: Model '{seg}' in filter path not found, skipping filter[/yellow]")
                break

            target_table = target_model["table_name"]

            # Find the FK on current_model that points to target_table
            fk = _find_fk_to_table(current_model, target_table, model_lookup)
            if not fk:
                # Try reverse: find FK on target_model that points back to prev_table
                fk = _find_fk_to_table(target_model, prev_table, model_lookup)
                if fk:
                    # Reverse join: target_model has FK pointing to prev_table
                    joins.append({
                        "from_table": prev_table,
                        "from_col": _quote_col(f"{target_table}.{fk['name']}"),
                        "to_table": target_table,
                        "to_col": _quote_col(f"{prev_table}.id"),
                        "model_name": target_model["name"],
                        "source_module": target_model["source_module"],
                    })
                else:
                    console.print(
                        f"[yellow]Warning: No FK found between '{current_model['name']}' "
                        f"and '{target_model['name']}', skipping filter[/yellow]"
                    )
                    break
            else:
                # Forward join: current_model has FK pointing to target_table
                joins.append({
                    "from_table": prev_table,
                    "from_col": _quote_col(f"{prev_table}.{fk['name']}"),
                    "to_table": target_table,
                    "to_col": _quote_col(f"{target_table}.id"),
                    "model_name": target_model["name"],
                    "source_module": target_model["source_module"],
                })

            prev_table = target_table
            current_model = target_model
        else:
            # All segments resolved successfully
            # fk_table is the table containing the filter_field FK column
            fk_table = joins[-1]["to_table"] if joins else source_table
            resolved = {
                "name": flt.get("i18n_key", filter_model_name),
                "filter_key": filter_model_name,
                "filter_field": filter_field,
                "filter_type": "fk",
                "filter_table": filter_table,
                "fk_table": fk_table,
                "fk_col": _quote_col(f"{fk_table}.{filter_field}"),
                "owner_model_class": current_model["name"],
                "owner_source_module": current_model["source_module"],
                "filter_id_col": _quote_col(f"{filter_table}.id"),
                "filter_model": filter_model_name,
                "filter_model_class": filter_model["name"],
                "filter_source_module": filter_model["source_module"],
                "filter_label_field": filter_label_field,
                "joins": joins,
            }
            resolved_filters.append(resolved)

    if resolved_filters:
        viz["resolved_filters"] = resolved_filters
        # Compute global joins: join the shortest common prefix across all filters
        first_tables = {j["to_table"] for j in resolved_filters[0]["joins"]}
        common_tables = set(first_tables)
        for rf in resolved_filters[1:]:
            common_tables &= {j["to_table"] for j in rf["joins"]}
        global_joins = [j for j in resolved_filters[0]["joins"] if j["to_table"] in common_tables]
        # Per-filter: only joins whose tables are NOT in global_joins
        for rf in resolved_filters:
            rf["new_joins"] = [j for j in rf["joins"] if j["to_table"] not in common_tables]
        viz["global_joins"] = global_joins


def _find_fk_to_table(
    model: ModelDefinition,
    target_table: str,
    model_lookup: dict[str, ModelDefinition],
) -> dict | None:
    """Find a foreign key on model that points to target_table."""
    for fk in model.get("foreign_keys", []):
        fk_target = fk.get("target_model", "")
        # Try model name lookup -> table name
        target_model = model_lookup.get(fk_target)
        if target_model and target_model["table_name"] == target_table:
            return {"name": fk["name"], "target_model": fk_target}
        # Try case-insensitive model name -> table name
        for key, candidate_model in model_lookup.items():
            if (
                key.lower() == fk_target.lower()
                and candidate_model["table_name"] == target_table
            ):
                return {"name": fk["name"], "target_model": fk_target}
        # Direct table name match (FK target_model might be a table name)
        if fk_target.lower().replace(" ", "_") == target_table.lower().replace(" ", "_"):
            return {"name": fk["name"], "target_model": fk_target}
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Phase 6 — Per-Model Code Generation
# ═══════════════════════════════════════════════════════════════════════════


def _generate_singleton(
    model: ModelDefinition,
    cwd: Path,
    backend_path: Path,
    is_postgresql: bool = False,
    theme_name: str = "normal",
) -> None:
    """Generate code for singleton / config models."""
    context = {"model": model, "is_postgresql": is_postgresql}
    frontend_path = get_project_paths(cwd).frontend
    is_config = (
        model["module_name"] == "system_config" and model["name"] == "SystemConfig"
    ) or (
        model["module_name"] == "custom_config" and model["name"] == "CustomConfig"
    )

    if not model.get("frontend_only"):
        for tpl in ("singleton_schema.py.j2", "singleton_crud.py.j2",
                     "singleton_service.py.j2", "singleton_api.py.j2"):
            generate_file(tpl, context, _backend_path(tpl, model, backend_path))
        generate_file(
            "singleton_frontend_service.ts.j2", context,
            frontend_path / "src" / "services" / f"{model['module_name']}.ts",
        )

    generate_file(
        "singleton_store.ts.j2", context,
        frontend_path / "src" / "stores" / f"use{model['name']}Store.ts",
    )

    if not is_config:
        generate_theme_file(
            "singleton_page.tsx.j2", context,
            frontend_path / "src" / "pages" / f"{model['module_name']}" / "index.tsx",
            theme_name,
        )


def _backend_path(tpl: str, model: ModelDefinition, backend_path: Path) -> Path:
    """Map a backend template name to its output path."""
    mapping = {
        "singleton_schema.py.j2": backend_path / "app" / "schemas" / f"{model['module_name']}.py",
        "singleton_crud.py.j2": backend_path / "app" / "cruds" / f"{model['module_name']}.py",
        "singleton_service.py.j2": backend_path / "app" / "services" / f"{model['module_name']}.py",
        "singleton_api.py.j2": backend_path / "app" / "api" / "endpoints" / f"{model['module_name']}.py",
        "schema.py.j2": backend_path / "app" / "schemas" / f"{model['module_name']}.py",
        "user_schema.py.j2": backend_path / "app" / "schemas" / f"{model['module_name']}.py",
        "crud.py.j2": backend_path / "app" / "cruds" / f"{model['module_name']}.py",
        "user_crud.py.j2": backend_path / "app" / "cruds" / f"{model['module_name']}.py",
        "service.py.j2": backend_path / "app" / "services" / f"{model['module_name']}.py",
        "user_service.py.j2": backend_path / "app" / "services" / f"{model['module_name']}.py",
        "api.py.j2": backend_path / "app" / "api" / "endpoints" / f"{model['module_name']}.py",
        "read_only_api.py.j2": backend_path / "app" / "api" / "endpoints" / f"{model['module_name']}.py",
        "backend_test.py.j2": backend_path / "tests" / f"test_{model['module_name']}_api.py",
    }
    return mapping[tpl]


def _generate_regular_model(
    model: ModelDefinition,
    cwd: Path,
    backend_path: Path,
    is_postgresql: bool = False,
    theme_name: str = "normal",
) -> None:
    """Generate code for a regular (non-singleton, non-link) model."""
    context = {"model": model, "is_postgresql": is_postgresql}
    frontend_path = get_project_paths(cwd).frontend
    is_user_model = model["name"] == "User"

    tpl_schema = "user_schema.py.j2" if is_user_model else "schema.py.j2"
    tpl_crud = "user_crud.py.j2" if is_user_model else "crud.py.j2"
    tpl_service = "user_service.py.j2" if is_user_model else "service.py.j2"

    # Latest tables are internal companions — no direct CRUD, API, or frontend
    if model.get("is_latest_table"):
        return

    generate_file(tpl_schema, context, _backend_path(tpl_schema, model, backend_path))
    generate_file(tpl_crud, context, _backend_path(tpl_crud, model, backend_path))
    generate_file(tpl_service, context, _backend_path(tpl_service, model, backend_path))
    api_template = "read_only_api.py.j2" if model.get("read_only") else "api.py.j2"
    generate_file(api_template, context, _backend_path(api_template, model, backend_path))

    generate_file(
        "frontend_service.ts.j2", context,
        frontend_path / "src" / "services" / f"{model['module_name']}.ts",
    )

    # Timeseries models: no standalone pages/store — data is shown on parent entity detail
    if model.get("is_timescaledb") or model.get("is_latest_table"):
        return

    # Embedded relations reuse the child list/store inside a parent detail tab.
    # Generate that reusable page independently of whether the child also has
    # standalone routes of its own.
    standalone = model.get("standalone", True)
    has_embedded_page = model.get("has_embedded_page", False)

    if standalone or has_embedded_page:
        generate_file(
            "frontend_store.ts.j2", context,
            frontend_path / "src" / "stores" / f"use{model['name']}Store.ts",
        )

    if has_embedded_page:
        generate_theme_file(
            "frontend_page_list.tsx.j2", context,
            frontend_path / "src" / "pages" / model["module_name"] / "embedded.tsx",
            theme_name,
        )

    if not standalone:
        # A model may have been standalone in an earlier generation. Remove
        # those obsolete pages so TypeScript does not compile stale ID-based
        # code after the model becomes embedded-only.
        page_dir = frontend_path / "src" / "pages" / model["module_name"]
        for filename in ("index.tsx", "detail.tsx", "create.tsx"):
            (page_dir / filename).unlink(missing_ok=True)
        return

    generate_theme_file(
        "frontend_page_list.tsx.j2", context,
        frontend_path / "src" / "pages" / f"{model['module_name']}" / "index.tsx",
        theme_name,
    )
    generate_theme_file(
        "frontend_page_detail.tsx.j2", context,
        frontend_path / "src" / "pages" / f"{model['module_name']}" / "detail.tsx",
        theme_name,
    )

    if model.get("page_edit"):
        generate_theme_file(
            "frontend_page_create.tsx.j2", context,
            frontend_path / "src" / "pages" / f"{model['module_name']}" / "create.tsx",
            theme_name,
        )

    if not model.get("frontend_only") and not model.get("read_only"):
        generate_file(
            "backend_test.py.j2", context,
            _backend_path("backend_test.py.j2", model, backend_path),
        )


def _generate_export_handlers(model: ModelDefinition, backend_path: Path) -> None:
    """Generate background import/export handlers for configured models."""
    output_path = (
        backend_path / "app" / "handlers" / f"export_{model['module_name']}.py"
    )
    if not (model.get("importable") or model.get("exportable")):
        output_path.unlink(missing_ok=True)
        return

    generate_file(
        "export_handler.py.j2",
        {"model": model},
        output_path,
    )


def _generate_custom_io_handler(
    model: ModelDefinition, cwd: Path, backend_path: Path
) -> None:
    """Create and sync the developer-owned custom import/export hook."""
    if not (model.get("custom_importable") or model.get("custom_exportable")):
        return

    source_custom_io_path = get_project_paths(cwd).source / "custom_io"
    generated_custom_io_path = backend_path / "app" / "custom_io"
    source_custom_io_path.mkdir(parents=True, exist_ok=True)
    (source_custom_io_path / "__init__.py").touch(exist_ok=True)
    generate_file_if_missing(
        "custom_io.py.j2",
        {"model": model},
        source_custom_io_path / f"{model['module_name']}.py",
    )
    copy_file_with_status(
        source_custom_io_path / "__init__.py",
        generated_custom_io_path / "__init__.py",
    )
    copy_file_with_status(
        source_custom_io_path / f"{model['module_name']}.py",
        generated_custom_io_path / f"{model['module_name']}.py",
    )


def _sort_api_models(api_models: list[ModelDefinition]) -> list[ModelDefinition]:
    """Keep generated API files deterministic without coupling them to navigation."""
    api_models.sort(key=lambda m: m["module_name"])
    return api_models


def _navigation_visibility(raw: Any) -> dict[str, bool]:
    """Normalize an optional navigation-group visibility declaration."""
    roles = ("user", "admin", "developer")
    if isinstance(raw, list):
        return {role: role in raw for role in roles}
    if isinstance(raw, dict):
        return {role: bool(raw.get(role, False)) for role in roles}
    return {role: True for role in roles}


def _is_menu_model(model: ModelDefinition) -> bool:
    """Exclude configuration records that have dedicated system UI."""
    return not (
        model.get("module_name") in {"system_config", "custom_config"}
        and model.get("is_singleton")
    )


def _model_menu_node(model: ModelDefinition) -> dict[str, Any]:
    route = f"/{model['module_name']}" if model.get("is_singleton") else f"/{model['module_name']}s"
    return {
        "type": "item",
        "key": route,
        "icon": model.get("icon", "LayoutDashboard"),
        "label": f"models.{model['module_name']}.name",
        "my_label": (
            f"models.{model['module_name']}.my_name"
            if model.get("owner_field")
            else None
        ),
        "visible": model["role_visible"],
    }


def _custom_route_menu_node(route: dict[str, Any]) -> dict[str, Any]:
    menu = route.get("menu")
    if menu is None:
        raise ValueError(
            f"Frontend route '{route['id']}' is referenced by navigation but has no menu metadata."
        )
    return {
        "type": "item",
        "key": route["path"],
        "icon": menu["icon"],
        "label": menu["label"],
        "my_label": None,
        "visible": menu["visible"],
    }


def _builtin_menu_node(
    key: str,
    *,
    reports_enabled: bool,
    reports_role_visible: dict[str, bool],
    external_resources_enabled: bool = False,
    import_export_enabled: bool = False,
    import_export_role_visible: dict[str, bool] | None = None,
) -> dict[str, Any] | None:
    builtins = {
        "dashboard": {
            "key": "/dashboard",
            "icon": "Home",
            "label": "menu.dashboard",
            "visible": {"user": True, "admin": True, "developer": True},
        },
        "reports": {
            "key": "/reports",
            "icon": "FileBarChart",
            "label": "menu.reports",
            "visible": reports_role_visible,
        },
        "external-resources": {
            "key": "/external-resources",
            "icon": "RefreshCw",
            "label": "menu.external_resources",
            "visible": {"user": False, "admin": True, "developer": True},
        },
        "task-center": {
            "key": "/task-center",
            "icon": "ArrowRightLeft",
            "label": "menu.task_center",
            "visible": import_export_role_visible
            or {"user": False, "admin": False, "developer": False},
        },
    }
    if key == "reports" and not reports_enabled:
        return None
    if key == "external-resources" and not external_resources_enabled:
        return None
    if key == "task-center" and not import_export_enabled:
        return None
    node = builtins[key]
    return {"type": "item", **node}


def _build_navigation(
    navigation: Any,
    frontend_models: list[ModelDefinition],
    custom_routes: list[dict[str, Any]] | None = None,
    *,
    reports_enabled: bool,
    reports_role_visible: dict[str, bool],
    external_resources_enabled: bool = False,
    import_export_enabled: bool = False,
    import_export_role_visible: dict[str, bool] | None = None,
) -> list[dict[str, Any]]:
    """Build the generated menu tree from ``site_config.navigation``.

    When the setting is absent, preserve the historical flat menu shape. When
    it is present, its declarations lead the menu in tree order; menu-eligible
    models omitted from the tree are appended afterward in their default order.
    """
    custom_routes = custom_routes or []
    model_by_module = {
        model["module_name"]: model
        for model in frontend_models
        if _is_menu_model(model)
    }
    route_by_id = {route["id"]: route for route in custom_routes}

    def build_node(declaration: dict[str, Any], path: str) -> dict[str, Any] | None:
        node_type = declaration["type"]
        if node_type == "model":
            module_name = declaration["model"]
            model = model_by_module.get(module_name)
            if model is None:
                available = ", ".join(sorted(model_by_module)) or "(none)"
                raise ValueError(
                    f"site_config.navigation {path} references model '{module_name}', "
                    f"but its module name is not menu-eligible. Available models: {available}."
                )
            return _model_menu_node(model)
        if node_type == "route":
            route_id = declaration["route"]
            route = route_by_id.get(route_id)
            if route is None:
                available = ", ".join(sorted(route_by_id)) or "(none)"
                raise ValueError(
                    f"site_config.navigation {path} references frontend route "
                    f"'{route_id}', but it does not exist. Available routes: {available}."
                )
            return _custom_route_menu_node(route)
        if node_type == "builtin":
            return _builtin_menu_node(
                declaration["key"],
                reports_enabled=reports_enabled,
                reports_role_visible=reports_role_visible,
                external_resources_enabled=external_resources_enabled,
                import_export_enabled=import_export_enabled,
                import_export_role_visible=import_export_role_visible,
            )

        children = [
            built
            for index, child in enumerate(declaration["children"])
            if (built := build_node(child, f"{path}.children[{index}]")) is not None
        ]
        if not children:
            return None
        return {
            "type": "group",
            "key": f"group:{declaration['key']}",
            "label": f"menu.groups.{declaration['key']}",
            "icon": declaration.get("icon", "Folder"),
            "visible": _navigation_visibility(declaration.get("visible")),
            "default_open": bool(declaration.get("default_open", False)),
            "children": children,
            "translations": declaration["label"],
        }

    if navigation is None:
        default_nodes: list[dict[str, Any]] = [
            _builtin_menu_node(
                "dashboard",
                reports_enabled=reports_enabled,
                reports_role_visible=reports_role_visible,
                external_resources_enabled=external_resources_enabled,
                import_export_enabled=import_export_enabled,
                import_export_role_visible=import_export_role_visible,
            )
        ]
        default_nodes.extend(_model_menu_node(model) for model in model_by_module.values())
        default_nodes.extend(
            _custom_route_menu_node(route)
            for route in custom_routes
            if route.get("menu") is not None
        )
        for key in ("reports", "external-resources", "task-center"):
            node = _builtin_menu_node(
                key,
                reports_enabled=reports_enabled,
                reports_role_visible=reports_role_visible,
                external_resources_enabled=external_resources_enabled,
                import_export_enabled=import_export_enabled,
                import_export_role_visible=import_export_role_visible,
            )
            if node is not None:
                default_nodes.append(node)
        return default_nodes

    declared_nodes = [
        built
        for index, declaration in enumerate(navigation)
        if (built := build_node(declaration, f"navigation[{index}]")) is not None
    ]
    declared_models = {
        declaration["model"]
        for declaration in navigation
        if declaration["type"] == "model"
    }
    declared_models.update(
        child["model"]
        for declaration in navigation
        if declaration["type"] == "group"
        for child in declaration["children"]
        if child["type"] == "model"
    )
    declared_nodes.extend(
        _model_menu_node(model)
        for module_name, model in model_by_module.items()
        if module_name not in declared_models
    )
    declared_routes = {
        declaration["route"]
        for declaration in navigation
        if declaration["type"] == "route"
    }
    declared_routes.update(
        child["route"]
        for declaration in navigation
        if declaration["type"] == "group"
        for child in declaration["children"]
        if child["type"] == "route"
    )
    declared_nodes.extend(
        _custom_route_menu_node(route)
        for route in custom_routes
        if route.get("menu") is not None and route["id"] not in declared_routes
    )
    declared_builtins = {
        declaration["key"]
        for declaration in navigation
        if declaration["type"] == "builtin"
    }
    declared_builtins.update(
        child["key"]
        for declaration in navigation
        if declaration["type"] == "group"
        for child in declaration["children"]
        if child["type"] == "builtin"
    )
    if import_export_enabled and "task-center" not in declared_builtins:
        declared_nodes.append(
            _builtin_menu_node(
                "task-center",
                reports_enabled=reports_enabled,
                reports_role_visible=reports_role_visible,
                external_resources_enabled=external_resources_enabled,
                import_export_enabled=True,
                import_export_role_visible=import_export_role_visible,
            )
        )
    return declared_nodes


def phase_generate_per_model(
    models: list[ModelDefinition],
    site_config: dict,
    cwd: Path,
    backend_path: Path,
) -> list[ModelDefinition]:
    """Generate per-model files (schemas, CRUDs, services, APIs, frontend).

    Returns the sorted list of API-visible models for use in routing & navigation.
    """
    model_lookup = _build_model_lookup(models)
    is_postgresql = site_config.get("database_url", "").startswith("postgresql")
    theme_name = resolve_theme(site_config)[0]["id"]
    hidden_tasks = {
        (item["kind"], item["name"])
        for item in site_config.get("task_center", {}).get("hidden", [])
    }

    # Map each external model to one resource kind owned by a provider. Model
    # CUD operations become provider CUD calls through the delivery worker.
    for model in models:
        model["import_task_center_visible"] = (
            "import", model["module_name"]
        ) not in hidden_tasks
        model["export_task_center_visible"] = (
            "export", model["module_name"]
        ) not in hidden_tasks
        model["external_resource"] = _normalize_external_resource(
            model,
            model.get("site_props", {}).get("external_resource"),
        )

    # Resolve visualize filter paths for all models
    for model in models:
        _resolve_visualize_filters(model, model_lookup)

    for model in models:
        if model["is_link_table"] and not model.get("is_association_table"):
            continue

        # Generate one tracked background handler for every import/export model.
        _generate_export_handlers(model, backend_path)

        # Custom I/O hooks are developer-owned and never overwritten.
        _generate_custom_io_handler(model, cwd, backend_path)

        if model.get("is_singleton") or (
            model["module_name"] == "system_config" and model["name"] == "SystemConfig"
        ) or (
            model["module_name"] == "custom_config" and model["name"] == "CustomConfig"
        ):
            _generate_singleton(
                model,
                cwd,
                backend_path,
                is_postgresql=is_postgresql,
                theme_name=theme_name,
            )
        else:
            _generate_regular_model(
                model,
                cwd,
                backend_path,
                is_postgresql=is_postgresql,
                theme_name=theme_name,
            )

    api_models = [
        m for m in models
        if not m.get("frontend_only")
        and not m.get("is_latest_table")
        and (not m["is_link_table"] or (m.get("is_association_table") and m.get("show_in_menu")))
    ]
    return _sort_api_models(api_models)


# ═══════════════════════════════════════════════════════════════════════════
# Phase 7 — Aggregated Generation
# ═══════════════════════════════════════════════════════════════════════════


def _validate_notification_model(models: list[ModelDefinition]) -> tuple[bool, str]:
    """Check notification model requirements; return ``(enabled, api_base)``."""
    notification_model = next(
        (m for m in models if m.get("is_notification_table")), None
    )
    enabled = bool(notification_model)
    api_base = (
        f"/{notification_model['module_name']}s"
        if notification_model
        else "/notifications"
    )

    if notification_model:
        names = {f["name"] for f in notification_model.get("fields", [])}
        required = {"title", "summary", "content", "created_at", "is_read", "user_id"}
        missing = sorted(required - names)
        if missing:
            raise ValueError(
                f"Notification model '{notification_model['name']}' is missing "
                f"required fields: {', '.join(missing)}"
            )

    return enabled, api_base


def phase_generate_aggregated(
    models: list[ModelDefinition],
    api_models: list[ModelDefinition],
    site_config: dict,
    cwd: Path,
    backend_path: Path,
) -> None:
    """Generate cross-cutting files: router, routes, menu, dashboard, i18n, etc."""
    frontend_path = get_project_paths(cwd).frontend
    frontend_features = site_config.get("_frontend_features", [])
    frontend_routes = [
        {**route, "feature_name": feature["name"]}
        for feature in frontend_features
        for route in feature.get("routes", [])
    ]
    frontend_overrides = [
        {**override, "feature_name": feature["name"]}
        for feature in frontend_features
        for override in feature.get("overrides", [])
    ]
    dashboard_widgets = sorted(
        [
            {**widget, "feature_name": feature["name"]}
            for feature in frontend_features
            for widget in feature.get("dashboard_widgets", [])
        ],
        key=lambda widget: (widget["order"], widget["id"]),
    )
    theme_name = resolve_theme(site_config)[0]["id"]
    visualizations = site_config.get("_visualizations", [])
    public_dashboard = site_config.get("_public_dashboard", {"enabled": False})
    model_reports_enabled = any(model.get("reports") for model in api_models)
    import_export_models = [
        model
        for model in api_models
        if model.get("importable") or model.get("exportable")
    ]
    import_export_enabled = bool(import_export_models)
    tracking_enabled = any(
        model.get("tracked_operations")
        for model in models
        if model.get("module_name") != "operation_log"
    )
    scheduled_tasks = site_config.get("scheduled_tasks", [])
    tools = site_config.get("tools", [])
    hidden_tasks = {
        (item["kind"], item["name"])
        for item in site_config.get("task_center", {}).get("hidden", [])
    }
    background_tasks_enabled = bool(import_export_enabled or tools or scheduled_tasks)
    external_models = [m for m in models if m.get("external_resource")]
    external_resources_enabled = bool(external_models)
    configured_providers = site_config.get("providers", {})
    missing_providers = sorted({
        m["external_resource"]["provider"]
        for m in external_models
        if m["external_resource"]["provider"] not in configured_providers
    })
    if missing_providers:
        raise ValueError(
            "External-resource providers must be configured in site_config.providers: "
            + ", ".join(missing_providers)
        )
    resource_keys = [
        (m["external_resource"]["provider"], m["external_resource"]["resource"])
        for m in external_models
    ]
    duplicate_resource_keys = sorted({
        key for key in resource_keys if resource_keys.count(key) > 1
    })
    if duplicate_resource_keys:
        rendered = ", ".join(
            f"{provider}/{resource}" for provider, resource in duplicate_resource_keys
        )
        raise ValueError(
            "Each provider resource may map to only one model: " + rendered
        )
    external_resource_configs = [
        {
            "provider": m["external_resource"]["provider"],
            "resource": m["external_resource"]["resource"],
            "module": m["source_module"],
            "model": m["name"],
            "id_field": m["external_resource"].get("identity_field", "id"),
        }
        for m in external_models
    ]
    # ── TimescaleDB: collect models and generate db.py ──
    timescaledb_models = [m for m in models if m.get("is_timescaledb")]
    has_timescaledb = bool(timescaledb_models)
    # Collect _latest table module import paths so create_all registers them
    latest_table_imports = sorted({
        f"app.models.{m['source_module']}_latest"
        for m in timescaledb_models
    })
    model_imports = sorted({
        f"app.models.{m['source_module']}"
        for m in models
        if not m.get("frontend_only")
    })
    generated_indexes: list[dict[str, Any]] = []
    obsolete_indexes: list[dict[str, Any]] = []
    seen_indexes: set[tuple[str, tuple[str, ...]]] = set()

    def index_name(table: str, suffix: str) -> str:
        raw_name = f"ix_{table}_{suffix}"
        if len(raw_name.encode("utf-8")) > 63:
            import hashlib
            digest = hashlib.sha1(raw_name.encode("utf-8")).hexdigest()[:10]
            raw_name = f"{raw_name[:52]}_{digest}"
        return raw_name

    def add_index(table: str, columns: list[str], suffix: str) -> None:
        key = (table, tuple(columns))
        if key in seen_indexes:
            return
        seen_indexes.add(key)
        raw_name = index_name(table, suffix)
        sql = _render_create_index_sql(raw_name, table, columns)
        generated_indexes.append({"sql_literal": repr(sql)})

    def remove_obsolete_index(table: str, suffix: str) -> None:
        sql = f"DROP INDEX IF EXISTS {_quote_ddl_identifier(index_name(table, suffix))}"
        obsolete_indexes.append({"sql_literal": repr(sql)})

    for model in models:
        for fk in model.get("foreign_keys", []):
            if (
                model.get("is_timescaledb")
                and fk["name"] == model.get("timescaledb_entity_field")
            ):
                remove_obsolete_index(
                    model["table_name"], f"{fk['name']}_page"
                )
                continue
            columns = [fk["name"]]
            if model.get("has_created_at"):
                columns.append("created_at DESC")
            add_index(model["table_name"], columns, f"{fk['name']}_page")
    for model in timescaledb_models:
        entity = model["timescaledb_entity_field"]
        metric = model.get("timescaledb_metric_field")
        time_column = model["timescaledb_time_column"]
        add_index(
            model["table_name"], [entity, f"{time_column} DESC"],
            f"{entity}_{time_column}_desc",
        )
        if metric:
            suffix = f"{entity}_{metric}_{time_column}_desc"
            if model.get("primary_key_columns") == [entity, metric, time_column]:
                remove_obsolete_index(model["table_name"], suffix)
            else:
                add_index(
                    model["table_name"], [entity, metric, f"{time_column} DESC"],
                    suffix,
                )
    generate_file(
        "db.py.j2",
        {
            "tracking_enabled": tracking_enabled,
            "background_execution_enabled": bool(
                site_config.get("tools")
                or site_config.get("scheduled_tasks")
                or import_export_enabled
            ),
            "has_timescaledb": has_timescaledb,
            "timescaledb_models": timescaledb_models,
            "model_imports": model_imports,
            "latest_table_imports": latest_table_imports,
            "external_resources_enabled": external_resources_enabled,
            "generated_indexes": generated_indexes,
            "obsolete_indexes": obsolete_indexes,
        },
        backend_path / "app" / "core" / "db.py",
    )

    # ── Notification model lookup & WS ──
    notifications_enabled, notifications_api_base = _validate_notification_model(models)

    generate_file("ws.py.j2", {}, backend_path / "app" / "core" / "ws.py")
    generate_file(
        "ws_api.py.j2", {}, backend_path / "app" / "api" / "endpoints" / "ws.py"
    )

    # ── Task queue (always generated, needed if any model has async events) ──
    generate_file("task_queue.py.j2", {}, backend_path / "app" / "core" / "task_queue.py")

    if external_resources_enabled:
        external_context = {
            "resources_json": json.dumps(external_resource_configs, ensure_ascii=False),
        }
        generate_file(
            "external_resource_config.py.j2",
            external_context,
            backend_path / "app" / "core" / "external_resource_config.py",
        )
        generate_file(
            "external_resources.py.j2",
            {},
            backend_path / "app" / "core" / "external_resources.py",
        )
        generate_file(
            "external_resource_provider_registry.py.j2",
            {"providers": [
                {"name": name, "module": definition["module"]}
                for name, definition in sorted(configured_providers.items())
            ]},
            backend_path / "app" / "core" / "external_resource_provider_registry.py",
        )
        generate_file(
            "external_resources_api.py.j2",
            {},
            backend_path / "app" / "api" / "endpoints" / "external_resources.py",
        )
        generate_file(
            "frontend_external_resources_service.ts.j2",
            {},
            frontend_path / "src" / "services" / "external-resources.ts",
        )
        generate_file(
            "frontend_external_resources_page.tsx.j2",
            {},
            frontend_path / "src" / "pages" / "ExternalResources.tsx",
        )

    if visualizations:
        visualization_context = {
            "visualizations": visualizations,
            "visualizations_json": json.dumps(visualizations, ensure_ascii=False),
            "public_visualization_keys_json": json.dumps([
                item["key"] for item in public_dashboard.get("visualizations", [])
            ]),
        }
        generate_file(
            "visualization_runtime.py.j2",
            visualization_context,
            backend_path / "app" / "core" / "visualizations.py",
        )
        if public_dashboard.get("enabled"):
            generate_file(
                "public_dashboard_api.py.j2",
                {},
                backend_path / "app" / "api" / "endpoints" / "public_dashboard.py",
            )
        generate_file(
            "visualizations_api.py.j2",
            visualization_context,
            backend_path / "app" / "api" / "endpoints" / "visualizations.py",
        )
    # Model reports share the ECharts canvas and option builders with
    # configured dashboard visualizations.
    if visualizations or model_reports_enabled:
        visualization_context = {"visualizations": visualizations}
        generate_file(
            "frontend_visualization_service.ts.j2",
            visualization_context,
            frontend_path / "src" / "services" / "visualizations.ts",
        )
        generate_file(
            "frontend_visualization_chart.tsx.j2",
            {
                "visualizations": visualizations,
                "model_reports_enabled": model_reports_enabled,
            },
            frontend_path / "src" / "components" / "visualization-chart.tsx",
        )
    generate_file(
        "backend_main.py.j2",
        {
            "config": {
                **site_config,
                "external_resources_enabled": external_resources_enabled,
                "import_export_enabled": import_export_enabled,
                "background_tasks_enabled": background_tasks_enabled,
                "tracking_enabled": tracking_enabled,
            }
        },
        backend_path / "app" / "main.py",
    )

    # Custom backend source is mirrored after per-model generation so it stays
    # developer-owned. It lives in a dedicated generated namespace to avoid
    # collisions with framework and model modules.
    custom_api_modules = sync_custom_backend(
        cwd, backend_path, site_config.get("custom_features", [])
    )

    from ..agents import generate_agents
    generate_agents(site_config, api_models, cwd, backend_path)

    # ── API router ──
    update_api_router(
        api_models, backend_path / "app" / "api" / "api.py",
        scheduled_tasks=scheduled_tasks, tools=tools,
        agents_enabled=bool(site_config.get("agents")),
        external_resources_enabled=external_resources_enabled,
        visualizations_enabled=bool(visualizations),
        public_dashboard_enabled=bool(public_dashboard.get("enabled")),
        import_export_enabled=background_tasks_enabled,
        custom_api_modules=custom_api_modules,
    )

    if tools or scheduled_tasks or import_export_enabled:
        generate_file(
            "tool_execution_model.py.j2",
            {},
            backend_path / "app" / "core" / "background_execution.py",
        )
    if import_export_enabled:
        generate_file(
            "import_export_runtime.py.j2",
            {
                "tracked_io_operations": {
                    model["module_name"]: [
                        operation
                        for operation in model.get("tracked_operations", [])
                        if operation in {"import", "export"}
                    ]
                    for model in import_export_models
                    if any(
                        operation in {"import", "export"}
                        for operation in model.get("tracked_operations", [])
                    )
                }
            },
            backend_path / "app" / "core" / "import_export_runtime.py",
        )
    if tracking_enabled:
        generate_file(
            "operation_tracking.py.j2",
            {},
            backend_path / "app" / "core" / "operation_tracking.py",
        )
    else:
        (backend_path / "app" / "core" / "operation_tracking.py").unlink(
            missing_ok=True
        )
        if not any(model.get("module_name") == "operation_log" for model in models):
            stale_tracking_paths = [
                backend_path / "app" / area / "operation_log.py"
                for area in ("schemas", "cruds", "services", "api/endpoints")
            ] + [
                frontend_path / "src" / "services" / "operation_log.ts",
                frontend_path / "src" / "stores" / "useOperationLogStore.ts",
                frontend_path / "src" / "pages" / "operation_log" / "index.tsx",
                frontend_path / "src" / "pages" / "operation_log" / "detail.tsx",
                frontend_path / "src" / "pages" / "operation_log" / "create.tsx",
                frontend_path / "src" / "pages" / "operation_log" / "embedded.tsx",
            ]
            for stale_path in stale_tracking_paths:
                stale_path.unlink(missing_ok=True)
    if background_tasks_enabled:
        generate_file(
            "background_execution_cleanup.py.j2",
            {},
            backend_path / "app" / "core" / "background_execution_cleanup.py",
        )
        generate_file(
            "task_center_api.py.j2",
            {
                "scheduled_task_permissions": {
                    task["name"]: task.get("manual_permissions", [])
                    for task in scheduled_tasks
                },
                "hidden_tasks": [
                    {"kind": kind, "name": name}
                    for kind, name in sorted(hidden_tasks)
                ],
            },
            backend_path / "app" / "api" / "endpoints" / "task_center.py",
        )
    if tools:
        generate_file(
            "tool_runtime.py.j2",
            {},
            backend_path / "app" / "core" / "tool_runtime.py",
        )
        generate_file(
            "tool_registry.py.j2",
            {"tools": tools, "tools_json": json.dumps(tools, ensure_ascii=False)},
            backend_path / "app" / "core" / "tool_registry.py",
        )
        generate_file(
            "tools_api.py.j2",
            {"tools": tools},
            backend_path / "app" / "api" / "endpoints" / "tools.py",
        )
        generate_file(
            "tool_execution_handler.py.j2",
            {},
            backend_path / "app" / "handlers" / "tool_execution.py",
        )

    if scheduled_tasks:
        generate_file(
            "scheduled_task_runtime.py.j2",
            {},
            backend_path / "app" / "core" / "scheduled_task_runtime.py",
        )
        generate_file(
            "scheduled_task_bindings.py.j2",
            {
                "tasks": scheduled_tasks,
                "tasks_json": json.dumps(scheduled_tasks, ensure_ascii=False),
            },
            backend_path / "app" / "core" / "scheduled_task_bindings.py",
        )
        generate_file(
            "app_tasks_api.py.j2",
            {},
            backend_path / "app" / "api" / "endpoints" / "tasks.py",
        )
        generate_file(
            "scheduled_task_execution_handler.py.j2",
            {},
            backend_path / "app" / "handlers" / "scheduled_task_execution.py",
        )

    # ── Settings page ──
    system_model = next(
        (
            m
            for m in models
            if m["module_name"] == "system_config" and m["name"] == "SystemConfig"
        ),
        None,
    )
    site_name_field = next(
        (
            field
            for field in system_model["fields"]
            if field["name"] == "site_name"
        ),
        None,
    ) if system_model else None
    logo_field = next(
        (field for field in system_model["fields"] if field["name"] == "logo"),
        None,
    ) if system_model else None
    registration_field = next(
        (
            field
            for field in system_model["fields"]
            if field["name"] == "allow_registration"
        ),
        None,
    ) if system_model else None
    generate_file(
        "site_metadata.tsx.j2",
        {
            "system_model": system_model,
            "site_name_field": site_name_field,
            "logo_field": logo_field,
            "registration_field": registration_field,
        },
        frontend_path / "src" / "SiteMetadata.tsx",
    )
    custom_model = next(
        (
            m
            for m in models
            if m["module_name"] == "custom_config" and m["name"] == "CustomConfig"
        ),
        None,
    )
    generate_theme_file(
        "settings_page.tsx.j2",
        {"system_model": system_model, "custom_model": custom_model},
        frontend_path / "src" / "pages" / "Settings.tsx",
        theme_name,
    )

    # ── Profile page ──
    user_model = next((m for m in models if m["name"] == "User"), None)
    generate_file(
        "register_page.tsx.j2",
        {"model": user_model},
        frontend_path / "src" / "pages" / "Register.tsx",
    )
    if user_model is not None:
        generate_theme_file(
            "profile.tsx.j2",
            {"model": user_model},
            frontend_path / "src" / "pages" / "Profile.tsx",
            theme_name,
        )

    # ── Routes, Menu, Dashboard ──
    frontend_models = [
        m
        for m in api_models
        if not m.get("is_timescaledb")
        and not m.get("is_latest_table")
        and m.get("standalone", True)
    ]
    visualize_models = [
        m for m in api_models
        if not m.get("is_latest_table")
        and bool((m.get("visualize") or {}).get("show"))
    ]
    dashboard_models = [
        m for m in api_models
        if not m.get("is_latest_table") and m.get("dashboard_metrics")
    ]
    model_report_models = [
        m for m in api_models
        if not m.get("is_latest_table") and m.get("reports")
    ]
    report_models = model_report_models
    generated_route_paths = {
        "builtin.dashboard": "/dashboard",
        "builtin.settings": "/settings",
    }
    if site_config.get("agents"):
        generated_route_paths["builtin.agent"] = "/agent"
    if report_models:
        generated_route_paths["builtin.reports"] = "/reports"
    if external_resources_enabled:
        generated_route_paths["builtin.external-resources"] = "/external-resources"
    if background_tasks_enabled:
        generated_route_paths["builtin.task-center"] = "/task-center"
    for model in frontend_models:
        module_name = model["module_name"]
        if model.get("is_singleton"):
            generated_route_paths[f"model.{module_name}.detail"] = f"/{module_name}"
            continue
        generated_route_paths[f"model.{module_name}.list"] = f"/{module_name}s"
        generated_route_paths[f"model.{module_name}.detail"] = f"/{module_name}s/:id"
        if model.get("page_edit"):
            generated_route_paths[f"model.{module_name}.create"] = f"/{module_name}s/new"

    reserved_route_paths = {
        "/login", "/register", "/error/:code", "/profile",
        *generated_route_paths.values(),
    }
    for route in frontend_routes:
        if route["path"] in reserved_route_paths:
            raise ValueError(
                f"Frontend route '{route['id']}' conflicts with generated path "
                f"'{route['path']}'. Use a CustomOverride for generated pages."
            )
    unknown_overrides = sorted(
        override["target"]
        for override in frontend_overrides
        if override["target"] not in generated_route_paths
    )
    if unknown_overrides:
        raise ValueError(
            "Frontend overrides reference unavailable generated routes: "
            + ", ".join(unknown_overrides)
            + ". Available targets: "
            + ", ".join(sorted(generated_route_paths))
        )
    reports_role_visible = {
        role: any(
            role in model.get("reports", {}).get("permitted_roles", [])
            for model in report_models
        )
        for role in ("user", "admin", "developer")
    }
    import_export_role_visible = {
        role: (
            any(
                role in tool.get("permissions", [])
                and ("tool", tool["name"]) not in hidden_tasks
                for tool in tools
            )
            or any(
                role in task.get("manual_permissions", [])
                and ("scheduled_task", task["name"]) not in hidden_tasks
                for task in scheduled_tasks
            )
            or any(
                bool(model.get("role_visible", {}).get(role, False))
                and (
                    (
                        bool(model.get("exportable"))
                        and "r" in model.get("role_permissions", {}).get(role, "")
                        and ("export", model["module_name"]) not in hidden_tasks
                    )
                    or (
                        bool(model.get("importable"))
                        and "c" in model.get("role_permissions", {}).get(role, "")
                        and "u" in model.get("role_permissions", {}).get(role, "")
                        and ("import", model["module_name"]) not in hidden_tasks
                    )
                )
                for model in import_export_models
            )
        )
        for role in ("user", "admin", "developer")
    }
    navigation = _build_navigation(
        site_config.get("navigation"),
        frontend_models,
        frontend_routes,
        reports_enabled=bool(report_models),
        reports_role_visible=reports_role_visible,
        external_resources_enabled=external_resources_enabled,
        import_export_enabled=background_tasks_enabled,
        import_export_role_visible=import_export_role_visible,
    )
    if site_config.get("agents"):
        navigation.append({
            "type": "item", "key": "/agent", "icon": "MessageSquare",
            "label": "agent.title", "my_label": None,
            "visible": {
                role: any(role in agent["roles"] for agent in site_config["agents"].values())
                for role in ("user", "admin", "developer")
            },
        })
    if background_tasks_enabled:
        generate_file(
            "frontend_task_center_service.ts.j2",
            {},
            frontend_path / "src" / "services" / "task-center.ts",
        )
        generate_file(
            "frontend_task_center_page.tsx.j2",
            {
                "io_models": import_export_models,
                "tools": tools,
                "scheduled_tasks": scheduled_tasks,
                "task_names": sorted({
                    model["module_name"]
                    for model in import_export_models
                    if (
                        (model.get("importable") and ("import", model["module_name"]) not in hidden_tasks)
                        or (model.get("exportable") and ("export", model["module_name"]) not in hidden_tasks)
                    )
                } | {
                    tool["name"]
                    for tool in tools
                    if ("tool", tool["name"]) not in hidden_tasks
                } | {
                    task["name"]
                    for task in scheduled_tasks
                    if ("scheduled_task", task["name"]) not in hidden_tasks
                }),
            },
            frontend_path / "src" / "pages" / "TaskCenter.tsx",
        )
    generate_file(
        "frontend_feature_routes.tsx.j2",
        {"routes": frontend_routes, "overrides": frontend_overrides},
        frontend_path / "src" / "GeneratedFeatureRoutes.tsx",
    )
    generate_file(
        "frontend_routes.tsx.j2",
        {
            "models": frontend_models,
            "external_resources_enabled": external_resources_enabled,
            "reports_enabled": bool(report_models),
            "import_export_enabled": background_tasks_enabled,
            "public_dashboard": public_dashboard,
            "agents_enabled": bool(site_config.get("agents")),
        },
        frontend_path / "src" / "Routes.tsx",
    )
    # Collect icons from both model items and declared navigation groups.
    def collect_navigation_icons(nodes: list[dict[str, Any]]) -> set[str]:
        icons: set[str] = set()
        for node in nodes:
            icons.add(node["icon"])
            icons.update(collect_navigation_icons(node.get("children", [])))
        return icons

    used_icons = sorted(collect_navigation_icons(navigation))
    generate_file(
        "frontend_menu.tsx.j2",
        {"navigation": navigation, "used_icons": used_icons},
        frontend_path / "src" / "Menu.tsx",
    )
    generate_file(
        "frontend_dashboard_widgets.tsx.j2",
        {"widgets": dashboard_widgets},
        frontend_path / "src" / "GeneratedDashboardWidgets.tsx",
    )
    site_logger_enabled = "site_logger" in site_config.get("plugins", [])
    show_dashboard_announcement = bool(
        system_model
        and any(
            field["name"] == "announcement_content"
            and "r" in field.get("permissions", "")
            for field in system_model["fields"]
        )
    )
    dashboard_metric_icons = sorted({
        metric.get("icon", "Activity")
        for model in dashboard_models
        for metric in model.get("dashboard_metrics", [])
    })
    generate_theme_file(
        "dashboard_page.tsx.j2",
        {
            "models": visualize_models,
            "dashboard_models": dashboard_models,
            "scheduled_tasks": scheduled_tasks,
            "site_logger": site_logger_enabled,
            "show_dashboard_announcement": show_dashboard_announcement,
            "tools": tools,
            "dashboard_metric_icons": dashboard_metric_icons,
            "visualizations": visualizations,
            "public_dashboard": public_dashboard,
            "dashboard_widgets": dashboard_widgets,
        },
        frontend_path / "src" / "pages" / "Dashboard.tsx",
        theme_name,
    )
    if public_dashboard.get("enabled") and not public_dashboard.get("component"):
        generate_file(
            "public_dashboard_page.tsx.j2",
            {"public_dashboard": public_dashboard},
            frontend_path / "src" / "pages" / "PublicDashboard.tsx",
        )
    if report_models:
        generate_file(
            "report_runtime.py.j2",
            {},
            backend_path / "app" / "core" / "reports.py",
        )
        generate_file(
            "model_report_page.tsx.j2",
            {"report_models": model_report_models},
            frontend_path / "src" / "pages" / "Reports.tsx",
        )

    # ── Feature flags ──
    generate_file(
        "frontend_features.ts.j2",
        {
            "notifications_enabled": notifications_enabled,
            "notifications_api_base": notifications_api_base,
        },
        frontend_path / "src" / "features.ts",
    )

    # ── Scheduled task service/store ──
    if scheduled_tasks:
        generate_file(
            "frontend_task_service.ts.j2", {},
            frontend_path / "src" / "services" / "tasks.ts",
        )
        generate_file(
            "task_store.ts.j2", {},
            frontend_path / "src" / "stores" / "useTaskStore.ts",
        )

    if tools:
        generate_file(
            "frontend_tool_service.ts.j2",
            {},
            frontend_path / "src" / "services" / "tools.ts",
        )
        generate_file(
            "frontend_dashboard_tools.tsx.j2",
            {"tools": tools},
            frontend_path / "src" / "components" / "dashboard-tools.tsx",
        )

    # ── Locale files ──
    navigation_groups = [node for node in navigation if node["type"] == "group"]
    generate_locale_files(
        models,
        frontend_path / "src" / "locales",
        navigation_groups,
        frontend_features,
    )

    # ── Background task handlers __init__.py ──
    # Match the models that received a routed API and the shared I/O runtime;
    # frontend-only and internal link models must not import unavailable handlers.
    export_models = import_export_models
    generate_file(
        "handlers_init.py.j2",
        {
            "export_models": export_models,
            "tools_enabled": bool(tools),
            "scheduled_tasks_enabled": bool(scheduled_tasks),
        },
        backend_path / "app" / "handlers" / "__init__.py",
    )
