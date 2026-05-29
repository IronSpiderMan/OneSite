"""Phases 6 & 7 — Code generation.

Phase 6  — Per-model generation: schemas, CRUDs, services, API endpoints,
           frontend services, stores, pages, and backend tests.

Phase 7 — Aggregated / cross-cutting generation: API router, route tables,
          menu, dashboard, settings, profile, i18n locale files, WebSocket
          scaffolding, task pages, and feature flags.
"""

from pathlib import Path

from ..i18n import generate_locale_files
from ..render import generate_file
from ..router import update_api_router
from ..types import ModelDefinition
from .base import console


# ═══════════════════════════════════════════════════════════════════════════
# Phase 6 — Per-Model Code Generation
# ═══════════════════════════════════════════════════════════════════════════


def _generate_singleton(model: ModelDefinition, cwd: Path, backend_path: Path, is_postgresql: bool = False) -> None:
    """Generate code for singleton / config models."""
    context = {"model": model, "is_postgresql": is_postgresql}
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
            cwd / "frontend" / "src" / "services" / f"{model['module_name']}.ts",
        )

    generate_file(
        "singleton_store.ts.j2", context,
        cwd / "frontend" / "src" / "stores" / f"use{model['name']}Store.ts",
    )

    if not is_config:
        generate_file(
            "singleton_page.tsx.j2", context,
            cwd / "frontend" / "src" / "pages" / f"{model['module_name']}" / "index.tsx",
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


def _generate_regular_model(model: ModelDefinition, cwd: Path, backend_path: Path, is_postgresql: bool = False) -> None:
    """Generate code for a regular (non-singleton, non-link) model."""
    context = {"model": model, "is_postgresql": is_postgresql}
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
        cwd / "frontend" / "src" / "services" / f"{model['module_name']}.ts",
    )

    # Timeseries models: no standalone pages/store — data is shown on parent entity detail
    if model.get("is_timescaledb") or model.get("is_latest_table"):
        return

    generate_file(
        "frontend_store.ts.j2", context,
        cwd / "frontend" / "src" / "stores" / f"use{model['name']}Store.ts",
    )
    generate_file(
        "frontend_page_list.tsx.j2", context,
        cwd / "frontend" / "src" / "pages" / f"{model['module_name']}" / "index.tsx",
    )
    generate_file(
        "frontend_page_detail.tsx.j2", context,
        cwd / "frontend" / "src" / "pages" / f"{model['module_name']}" / "detail.tsx",
    )

    if model.get("page_edit"):
        generate_file(
            "frontend_page_create.tsx.j2", context,
            cwd / "frontend" / "src" / "pages" / f"{model['module_name']}" / "create.tsx",
        )

    if not model.get("frontend_only"):
        generate_file(
            "backend_test.py.j2", context,
            _backend_path("backend_test.py.j2", model, backend_path),
        )


def _generate_event_listeners(model: ModelDefinition, backend_path: Path) -> None:
    """Generate event listener file for a model that has on_before_*/on_after_* methods."""
    listeners = model.get("event_listeners", [])
    if not listeners:
        return

    generate_file(
        "events.py.j2",
        {"model": model},
        backend_path / "app" / "events" / f"{model['module_name']}.py",
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
    is_postgresql = site_config.get("database_url", "").startswith("postgresql")

    for model in models:
        if model["is_link_table"] and not model.get("is_association_table"):
            continue

        # Generate event listener file if the model has on_before_*/on_after_* methods
        _generate_event_listeners(model, backend_path)

        if model.get("is_singleton") or (
            model["module_name"] == "system_config" and model["name"] == "SystemConfig"
        ) or (
            model["module_name"] == "custom_config" and model["name"] == "CustomConfig"
        ):
            _generate_singleton(model, cwd, backend_path, is_postgresql=is_postgresql)
        else:
            _generate_regular_model(model, cwd, backend_path, is_postgresql=is_postgresql)

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
    # ── TimescaleDB: collect models and generate db.py ──
    timescaledb_models = [m for m in models if m.get("is_timescaledb")]
    has_timescaledb = bool(timescaledb_models)
    generate_file(
        "db.py.j2",
        {
            "has_timescaledb": has_timescaledb,
            "timescaledb_models": timescaledb_models,
        },
        backend_path / "app" / "core" / "db.py",
    )

    # ── Notification model lookup & WS ──
    notifications_enabled, notifications_api_base = _validate_notification_model(models)

    generate_file("ws.py.j2", {}, backend_path / "app" / "core" / "ws.py")
    generate_file(
        "ws_api.py.j2", {}, backend_path / "app" / "api" / "endpoints" / "ws.py"
    )

    # ── API router ──
    scheduled_tasks = site_config.get("scheduled_tasks", [])
    update_api_router(
        api_models, backend_path / "app" / "api" / "api.py", scheduled_tasks
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
    custom_model = next(
        (
            m
            for m in models
            if m["module_name"] == "custom_config" and m["name"] == "CustomConfig"
        ),
        None,
    )
    generate_file(
        "settings_page.tsx.j2",
        {"system_model": system_model, "custom_model": custom_model},
        cwd / "frontend" / "src" / "pages" / "Settings.tsx",
    )

    # ── Profile page ──
    user_model = next((m for m in models if m["name"] == "User"), None)
    if user_model is not None:
        generate_file(
            "profile.tsx.j2",
            {"model": user_model},
            cwd / "frontend" / "src" / "pages" / "Profile.tsx",
        )

    # ── Routes, Menu, Dashboard ──
    frontend_models = [
        m
        for m in api_models
        if not m.get("is_timescaledb") and not m.get("is_latest_table")
    ]
    generate_file(
        "frontend_routes.tsx.j2",
        {"models": frontend_models},
        cwd / "frontend" / "src" / "Routes.tsx",
    )
    generate_file(
        "frontend_menu.tsx.j2",
        {"models": frontend_models},
        cwd / "frontend" / "src" / "Menu.tsx",
    )
    generate_file(
        "dashboard_page.tsx.j2",
        {"models": frontend_models, "scheduled_tasks": scheduled_tasks},
        cwd / "frontend" / "src" / "pages" / "Dashboard.tsx",
    )

    # ── Feature flags ──
    generate_file(
        "frontend_features.ts.j2",
        {
            "notifications_enabled": notifications_enabled,
            "notifications_api_base": notifications_api_base,
        },
        cwd / "frontend" / "src" / "features.ts",
    )

    # ── Scheduled task service/store ──
    if scheduled_tasks:
        generate_file(
            "frontend_task_service.ts.j2", {},
            cwd / "frontend" / "src" / "services" / "tasks.ts",
        )
        generate_file(
            "task_store.ts.j2", {},
            cwd / "frontend" / "src" / "stores" / "useTaskStore.ts",
        )

    # ── Locale files ──
    generate_locale_files(models, cwd / "frontend" / "src" / "locales")

    # ── Event listeners __init__.py (imports all model event modules) ──
    event_models = [m for m in models if m.get("event_listeners")]
    if event_models:
        generate_file(
            "events_init.py.j2",
            {"event_models": event_models},
            backend_path / "app" / "events" / "__init__.py",
        )
