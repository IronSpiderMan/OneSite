"""Phases 6 & 7 — Code generation.

Phase 6  — Per-model generation: schemas, CRUDs, services, API endpoints,
           frontend services, stores, pages, and backend tests.

Phase 7 — Aggregated / cross-cutting generation: API router, route tables,
          menu, dashboard, settings, profile, i18n locale files, WebSocket
          scaffolding, task pages, and feature flags.
"""

import json
from pathlib import Path
from typing import Any

from ...project_paths import get_project_paths
from ..i18n import generate_locale_files
from ..render import generate_file, generate_theme_file
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


def _build_model_lookup(models: list[ModelDefinition]) -> dict[str, ModelDefinition]:
    """Build a dict mapping model names and table names to ModelDefinitions."""
    lookup: dict[str, ModelDefinition] = {}
    for m in models:
        lookup[m["name"]] = m
        lookup[m["table_name"]] = m
    return lookup


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
            fk = _find_fk_to_table(current_model, target_table)
            if not fk:
                # Try reverse: find FK on target_model that points back to prev_table
                fk = _find_fk_to_table(target_model, prev_table)
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


def _find_fk_to_table(model: ModelDefinition, target_table: str) -> dict | None:
    """Find a foreign key on model that points to target_table."""
    for fk in model.get("foreign_keys", []):
        fk_target = fk.get("target_model", "")
        # Try model name lookup -> table name
        target_model = model_lookup_global.get(fk_target)
        if target_model and target_model["table_name"] == target_table:
            return {"name": fk["name"], "target_model": fk_target}
        # Try case-insensitive model name -> table name
        for key, m in model_lookup_global.items():
            if key.lower() == fk_target.lower() and m["table_name"] == target_table:
                return {"name": fk["name"], "target_model": fk_target}
        # Direct table name match (FK target_model might be a table name)
        if fk_target.lower().replace(" ", "_") == target_table.lower().replace(" ", "_"):
            return {"name": fk["name"], "target_model": fk_target}
    return None


# Module-level lookup, populated before code generation
model_lookup_global: dict[str, ModelDefinition] = {}


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
    generate_file("api.py.j2", context, _backend_path("api.py.j2", model, backend_path))

    generate_file(
        "frontend_service.ts.j2", context,
        frontend_path / "src" / "services" / f"{model['module_name']}.ts",
    )

    # Timeseries models: no standalone pages/store — data is shown on parent entity detail
    if model.get("is_timescaledb") or model.get("is_latest_table"):
        return

    # Embedded-only models keep their backend API and frontend service, but
    # intentionally have no independent store, pages, or routes.
    if not model.get("standalone", True):
        return

    generate_file(
        "frontend_store.ts.j2", context,
        frontend_path / "src" / "stores" / f"use{model['name']}Store.ts",
    )
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

    if not model.get("frontend_only"):
        generate_file(
            "backend_test.py.j2", context,
            _backend_path("backend_test.py.j2", model, backend_path),
        )


def _generate_event_listeners(model: ModelDefinition, backend_path: Path) -> None:
    """Generate event listener file for a model that has low-level ORM hooks."""
    listeners = model.get("event_listeners", [])
    output_path = (
        backend_path / "app" / "events" / f"{model['module_name']}.py"
    )
    if not listeners:
        # Generated hooks may have been removed or renamed. Do not leave a
        # stale module behind for an old events/__init__.py to import.
        output_path.unlink(missing_ok=True)
        return

    generate_file(
        "events.py.j2",
        {"model": model},
        output_path,
    )


def _generate_task_handlers(model: ModelDefinition, backend_path: Path) -> None:
    """Generate handlers for explicit post-commit background hooks."""
    output_path = (
        backend_path / "app" / "handlers" / f"{model['module_name']}.py"
    )
    if not model.get("background_hooks"):
        # Remove handlers generated by the retired async-ORM behavior.
        output_path.unlink(missing_ok=True)
        return

    generate_file(
        "handler.py.j2",
        {"model": model},
        output_path,
    )


def _generate_export_handlers(model: ModelDefinition, backend_path: Path) -> None:
    """Generate background export handler file for exportable models."""
    if not model.get("exportable"):
        return

    generate_file(
        "export_handler.py.j2",
        {"model": model},
        backend_path / "app" / "handlers" / f"export_{model['module_name']}.py",
    )


def _sort_api_models(
    api_models: list[ModelDefinition], site_config: dict
) -> list[ModelDefinition]:
    """Apply ``nav_order`` sorting from *site_config*, falling back to alphabetical."""
    nav_order = site_config.get("nav_order", [])
    if isinstance(nav_order, list) and nav_order:
        order_map = {str(x): i for i, x in enumerate(nav_order)}
        api_models.sort(
            key=lambda m: (order_map.get(m["module_name"], 10_000), m["module_name"])
        )
    else:
        api_models.sort(key=lambda m: m["module_name"])
    return api_models


def phase_generate_per_model(
    models: list[ModelDefinition],
    site_config: dict,
    cwd: Path,
    backend_path: Path,
) -> list[ModelDefinition]:
    """Generate per-model files (schemas, CRUDs, services, APIs, frontend).

    Returns the sorted list of API-visible models for use in routing & navigation.
    """
    global model_lookup_global
    model_lookup_global = _build_model_lookup(models)
    is_postgresql = site_config.get("database_url", "").startswith("postgresql")
    theme_name = resolve_theme(site_config)[0]["id"]

    # External resources are declared on the target model. Resolve the reverse
    # dependency graph once so source-row changes can fan out reconciliation.
    by_key = {
        key: model
        for model in models
        for key in (model["name"], model["module_name"], model["table_name"])
    }
    for model in models:
        external = model.get("site_props", {}).get("external_resource")
        if external is None:
            model["external_resource"] = None
            continue
        if not isinstance(external, dict):
            raise ValueError(f"{model['name']} external_resource must be an object")
        missing = {"provider", "resource_type"} - set(external)
        if missing:
            raise ValueError(
                f"{model['name']} external_resource is missing: "
                + ", ".join(sorted(missing))
            )
        dependencies = external.get("depends_on", [])
        if not isinstance(dependencies, list):
            raise ValueError(
                f"{model['name']} external_resource.depends_on must be a list"
            )
        normalized = {**external, "depends_on": dependencies}
        model["external_resource"] = normalized
        for dependency in dependencies:
            if (
                not isinstance(dependency, dict)
                or not dependency.get("source")
                or not dependency.get("field")
            ):
                raise ValueError(
                    f"{model['name']} external_resource dependencies require source and field"
                )
            source = by_key.get(str(dependency["source"]))
            if source is None:
                raise ValueError(
                    f"{model['name']} external_resource dependency source "
                    f"'{dependency['source']}' was not found"
                )
            source.setdefault("external_resource_dependents", []).append(
                {
                    "target_resource_type": normalized["resource_type"],
                    "target_module": model["source_module"],
                    "target_model": model["name"],
                    "target_field": dependency["field"],
                }
            )

    # Resolve visualize filter paths for all models
    for model in models:
        _resolve_visualize_filters(model, model_lookup_global)

    for model in models:
        if model["is_link_table"] and not model.get("is_association_table"):
            continue

        # Generate event listener file if the model has low-level ORM hooks.
        _generate_event_listeners(model, backend_path)

        # Generate handlers for explicit on_background_after_* methods.
        _generate_task_handlers(model, backend_path)

        # Generate background export handler file if model is exportable
        _generate_export_handlers(model, backend_path)

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
    return _sort_api_models(api_models, site_config)


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
    theme_name = resolve_theme(site_config)[0]["id"]
    external_models = [m for m in models if m.get("external_resource")]
    external_resources_enabled = bool(external_models)
    external_resource_configs = [
        {
            "provider": m["external_resource"]["provider"],
            "resource_type": m["external_resource"]["resource_type"],
            "module": m["source_module"],
            "model": m["name"],
            "id_field": m["external_resource"].get("identity_field", "id"),
            "depends_on": m["external_resource"].get("depends_on", []),
            "health": m["external_resource"].get("health"),
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
    generate_file(
        "db.py.j2",
        {
            "background_execution_enabled": bool(
                site_config.get("tools") or site_config.get("scheduled_tasks")
            ),
            "has_timescaledb": has_timescaledb,
            "timescaledb_models": timescaledb_models,
            "latest_table_imports": latest_table_imports,
            "external_resources_enabled": external_resources_enabled,
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
            "external_resources.py.j2",
            external_context,
            backend_path / "app" / "core" / "external_resources.py",
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

    generate_file(
        "backend_main.py.j2",
        {"config": {**site_config, "external_resources_enabled": external_resources_enabled}},
        backend_path / "app" / "main.py",
    )

    # ── API router ──
    scheduled_tasks = site_config.get("scheduled_tasks", [])
    tools = site_config.get("tools", [])
    update_api_router(
        api_models,
        backend_path / "app" / "api" / "api.py",
        scheduled_tasks,
        tools,
        external_resources_enabled,
    )

    if tools or scheduled_tasks:
        generate_file(
            "tool_execution_model.py.j2",
            {},
            backend_path / "app" / "core" / "background_execution.py",
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
    dashboard_models = [
        m for m in api_models
        if not m.get("is_latest_table") and m.get("dashboard_metrics")
    ]
    generate_file(
        "frontend_routes.tsx.j2",
        {"models": frontend_models, "external_resources_enabled": external_resources_enabled},
        frontend_path / "src" / "Routes.tsx",
    )
    # Collect unique icon names used across models (for dynamic import)
    used_icons = sorted({m.get("icon", "LayoutDashboard") for m in frontend_models})
    generate_file(
        "frontend_menu.tsx.j2",
        {"models": frontend_models, "used_icons": used_icons, "external_resources_enabled": external_resources_enabled},
        frontend_path / "src" / "Menu.tsx",
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
            "models": frontend_models,
            "dashboard_models": dashboard_models,
            "scheduled_tasks": scheduled_tasks,
            "site_logger": site_logger_enabled,
            "show_dashboard_announcement": show_dashboard_announcement,
            "tools": tools,
            "dashboard_metric_icons": dashboard_metric_icons,
        },
        frontend_path / "src" / "pages" / "Dashboard.tsx",
        theme_name,
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
    generate_locale_files(models, frontend_path / "src" / "locales")

    # ── Event listeners __init__.py (imports all model event modules) ──
    event_models = [m for m in models if m.get("event_listeners")]
    generate_file(
        "events_init.py.j2",
        {"event_models": event_models},
        backend_path / "app" / "events" / "__init__.py",
    )

    # ── Background task handlers __init__.py ──
    handler_models = [
        m for m in models
        if m.get("background_hooks")
    ]
    export_models = [m for m in models if m.get("exportable")]
    generate_file(
        "handlers_init.py.j2",
        {
            "handler_models": handler_models,
            "export_models": export_models,
            "tools_enabled": bool(tools),
            "scheduled_tasks_enabled": bool(scheduled_tasks),
        },
        backend_path / "app" / "handlers" / "__init__.py",
    )
