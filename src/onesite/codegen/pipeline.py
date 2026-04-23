import importlib
import inspect
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

from pydantic_core import PydanticUndefined
from rich.console import Console
from sqlmodel import SQLModel
import sqlmodel.main

from .assets import sync_backend_assets, sync_frontend_assets
from .config import load_site_config
from .envsync import sync_env_files
from .i18n import generate_locale_files
from .introspect import get_model_fields
from .render import generate_file
from .router import update_api_router
from .theme import resolve_theme

console = Console()

def _to_snake(name: str) -> str:
    import re

    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

def _install_snake_case_tablenames() -> None:
    if getattr(sqlmodel.main, "_onesite_snake_tablename_installed", False):
        return

    original_new = sqlmodel.main.SQLModelMetaclass.__new__

    def patched_new(mcls, name, bases, dict_, **kwargs):
        if kwargs.get("table", False) and "__tablename__" not in dict_:
            dict_["__tablename__"] = _to_snake(name)
        return original_new(mcls, name, bases, dict_, **kwargs)

    sqlmodel.main.SQLModelMetaclass.__new__ = patched_new
    sqlmodel.main._onesite_snake_tablename_installed = True


def generate_code():
    cwd = Path(os.getcwd())
    site_config = load_site_config(cwd)

    site_config.setdefault("project_name", "MyApp")
    site_config.setdefault("database_url", "sqlite:///./app.db")
    site_config.setdefault("upload_dir", "uploads")
    site_config.setdefault("secret_key", "changeme")
    site_config.setdefault(
        "allowed_origins",
        [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
    )

    backend_path = cwd / "backend"
    sync_env_files(site_config, backend_path, cwd / "frontend")

    if not backend_path.exists():
        console.print("[red]Backend directory not found. Are you in the project root?[/red]")
        return

    models_src_dir = cwd / "models"
    models_dest_dir = backend_path / "app" / "models"
    template_models_dir = Path(__file__).resolve().parent.parent / "templates" / "models"

    models_dest_dir.mkdir(parents=True, exist_ok=True)
    (models_dest_dir / "__init__.py").touch(exist_ok=True)

    if models_src_dir.exists():
        console.print(f"[green]Syncing models from {models_src_dir} to {models_dest_dir}...[/green]")
        for model_file in models_src_dir.glob("*.py"):
            shutil.copy2(model_file, models_dest_dir / model_file.name)
            console.print(f"Synced model: {model_file.name}")

    if template_models_dir.exists():
        for model_file in template_models_dir.glob("*.py"):
            target_in_project = models_src_dir / model_file.name
            if not target_in_project.exists():
                shutil.copy2(model_file, models_dest_dir / model_file.name)
                console.print(f"Synced base model from template: {model_file.name}")
            else:
                console.print(f"Skipping template model {model_file.name} (overridden in project)")

    _install_snake_case_tablenames()
    sys.path.insert(0, str(backend_path))
    try:
        import app.models  # noqa: F401
    except ImportError as e:
        console.print(f"[red]Could not import app.models: {e}[/red]")
        return

    models_dir = backend_path / "app" / "models"
    model_files = [f.stem for f in models_dir.glob("*.py") if f.stem != "__init__"]

    found_models: List[Dict[str, Any]] = []

    for module_name in model_files:
        full_module_name = f"app.models.{module_name}"
        try:
            if full_module_name in sys.modules:
                module = importlib.reload(sys.modules[full_module_name])
            else:
                module = importlib.import_module(full_module_name)
        except ImportError as e:
            console.print(f"[red]Error importing {full_module_name}: {e}[/red]")
            continue

        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, SQLModel) and obj is not SQLModel:
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
                        onesite_props.get("config_role")
                        or onesite_props.get("frontend_only")
                        or onesite_props.get("is_singleton")
                    )

                if hasattr(obj, "metadata") and (
                    getattr(obj, "__table__", None) is not None or singleton_marker or onesite_marker
                ):
                    model_module_name = _to_snake(name)
                    (
                        fields,
                        foreign_keys,
                        search_field,
                        unique_search_field,
                        is_link_table,
                        is_singleton,
                        model_permissions,
                        frontend_only,
                        translations,
                        auto_refresh,
                        refresh_interval,
                        reverse_fk_display,
                        model_site_props,
                        actions,
                        is_notification_table,
                        union_key,
                        importable,
                        exportable,
                        import_key,
                        role_permissions,
                        role_visible,
                        special_me_permissions,
                    ) = get_model_fields(obj, model_module_name)

                    if name == "User":
                        has_password = any(f["name"] == "password" for f in fields)
                        if not has_password:
                            fields.append(
                                {
                                    "name": "password",
                                    "type": "str",
                                    "ui_type": "str",
                                    "json_kind": None,
                                    "json_model_schema": None,
                                    "json_item_schema": None,
                                    "py_imports": [],
                                    "permissions": "cu",
                                    "create_optional": False,
                                    "update_optional": True,
                                    "required": True,
                                    "default": PydanticUndefined,
                                    "is_enum": False,
                                    "enum_values": [],
                                    "is_search_field": False,
                                    "fk_info": None,
                                    "allow_download": True,
                                    "label_key": "models.user.fields.password",
                                    "translations": {},
                                    "is_unique": False,
                                }
                            )

                    schema_imports = sorted({imp for f in fields for imp in f.get("py_imports", [])})

                    # Validate importable models have import_key
                    if importable:
                        if import_key:
                            # Use configured import_key
                            pass
                        elif any(f["name"] == "title" and f.get("is_unique") for f in fields):
                            # Default to title if it has unique constraint
                            import_key = "title"
                        else:
                            console.print(f"[red]Error: Model '{name}' has importable=True but no import_key configured.[/red]")
                            console.print(f"[red]Please set __onesite__ = {{'import_key': 'field_name'}} or ensure 'title' field has unique=True[/red]")
                            return

                    found_models.append(
                        {
                            "name": name,
                            "module_name": model_module_name,
                            "source_module": module_name,
                            "lower_name": name.lower(),
                            "fields": fields,
                            "schema_imports": schema_imports,
                            "foreign_keys": foreign_keys,
                            "search_field": search_field,
                            "unique_search_field": unique_search_field,
                            "is_link_table": is_link_table,
                            "is_singleton": is_singleton,
                            "model_permissions": model_permissions,
                            "role_permissions": role_permissions,
                            "role_visible": role_visible,
                            "special_me_permissions": special_me_permissions,
                            "frontend_only": frontend_only,
                            "translations": translations,
                            "auto_refresh": auto_refresh,
                            "refresh_interval": refresh_interval,
                            "reverse_fk_display": reverse_fk_display,
                            "site_props": model_site_props,
                            "actions": actions,
                            "is_notification_table": is_notification_table,
                            "union_key": union_key,
                            "importable": importable,
                            "exportable": exportable,
                            "import_key": import_key,
                            "visualize": model_site_props.get("visualize"),
                        }
                    )

    model_map = {m["name"]: m for m in found_models}
    module_map = {m["module_name"]: m for m in found_models}
    for model in found_models:
        model["reverse_foreign_keys"] = []
        model["m2m_fields"] = model.get("m2m_fields", [])
        model["reverse_m2m"] = model.get("reverse_m2m", [])
        if model.get("is_link_table"):
            order_field = next((f for f in model["fields"] if f["name"] == "order" and not f.get("fk_info")), None)
            model["link_order_field"] = "order" if order_field else None

            link_extra_fields = [
                f
                for f in model["fields"]
                if not f.get("fk_info") and f["name"] not in ["id", "order"]
            ]
            model["link_extra_fields"] = link_extra_fields
            model["is_association_table"] = len(link_extra_fields) > 0
        else:
            model["link_order_field"] = None
            model["link_extra_fields"] = []
            model["is_association_table"] = False
        if model.get("is_link_table") and model.get("is_association_table"):
            model["show_in_menu"] = bool(model.get("site_props", {}).get("show_in_menu", True))
        else:
            model["show_in_menu"] = True

    for model in found_models:
        for fk in model["foreign_keys"]:
            target_model = model_map.get(fk["target_model"])
            if target_model:
                fk["label_field"] = target_model.get("unique_search_field") or target_model["search_field"]
                fk["target_readable_fields"] = [
                    f
                    for f in target_model["fields"]
                    if "r" in f["permissions"] and f["name"] != "password" and not f.get("fk_info")
                ]

                if not model.get("is_link_table"):
                    base_name = model["module_name"]
                    if base_name.endswith("y") and base_name[-2] not in "aeiou":
                        reverse_name = f"{base_name[:-1]}ies"
                    else:
                        reverse_name = f"{base_name}s"

                    target_model["reverse_foreign_keys"].append(
                        {
                            "name": reverse_name,
                            "source_model": model["name"],
                            "source_service": model["module_name"],
                            "source_fk_field": fk["name"],
                            "label_field": model.get("unique_search_field") or model["search_field"],
                            "display": fk.get("reverse_display", True),
                        }
                    )

    for model in found_models:
        if model["is_link_table"]:
            fks = model["foreign_keys"]
            if len(fks) >= 2:
                m2m_cfg = {}
                if isinstance(model.get("site_props"), dict):
                    m2m_cfg = model["site_props"].get("m2m", {}) or {}
                directions = m2m_cfg.get("directions")
                if not isinstance(directions, list) or not directions:
                    directions = [
                        {
                            "from": fks[0]["target_service"],
                            "to": fks[1]["target_service"],
                            "editable": True,
                        }
                    ]

                editable_edges = set()
                for d in directions:
                    if not isinstance(d, dict):
                        continue
                    if d.get("editable", True):
                        editable_edges.add((str(d.get("from", "")), str(d.get("to", ""))))

                def find_fk_for(target_service: str, target_model: str):
                    return next(
                        (
                            fk
                            for fk in fks
                            if fk.get("target_service") == target_service or fk.get("target_model") == target_model
                        ),
                        None,
                    )

                for d in directions:
                    if not isinstance(d, dict):
                        continue
                    from_ref = str(d.get("from", "")).strip()
                    to_ref = str(d.get("to", "")).strip()
                    if not from_ref or not to_ref:
                        continue

                    from_model = module_map.get(from_ref) or model_map.get(from_ref)
                    to_model = module_map.get(to_ref) or model_map.get(to_ref)
                    if not from_model or not to_model:
                        continue

                    from_fk = find_fk_for(from_model["module_name"], from_model["name"])
                    to_fk = find_fk_for(to_model["module_name"], to_model["name"])
                    if not from_fk or not to_fk:
                        continue

                    if d.get("editable", True):
                        m2m_field_name = f"{to_model['lower_name']}_ids"
                        existing = next(
                            (
                                x
                                for x in from_model.get("m2m_fields", [])
                                if x.get("name") == m2m_field_name and x.get("target_model") == to_model["name"]
                            ),
                            None,
                        )
                        if not existing:
                            from_model["m2m_fields"].append(
                                {
                                    "name": m2m_field_name,
                                    "target_model": to_model["name"],
                                    "target_service": to_model["module_name"],
                                    "target_endpoint": f"{to_model['module_name']}s",
                                    "label_field": to_model.get("unique_search_field") or to_model["search_field"],
                                    "link_model": model["name"],
                                    "link_module": model["source_module"],
                                    "target_source_module": to_model["source_module"],
                                    "source_fk_field": from_fk["name"],
                                    "target_fk_field": to_fk["name"],
                                    "order_field": model.get("link_order_field"),
                                }
                            )

                    if (to_model["module_name"], from_model["module_name"]) in editable_edges:
                        continue

                    base_name = from_model["module_name"]
                    if base_name.endswith("y") and base_name[-2] not in "aeiou":
                        reverse_name = f"{base_name[:-1]}ies"
                    else:
                        reverse_name = f"{base_name}s"

                    existing_reverse = next(
                        (
                            x
                            for x in to_model.get("reverse_m2m", [])
                            if x.get("name") == reverse_name and x.get("source_model") == from_model["name"]
                        ),
                        None,
                    )
                    if not existing_reverse:
                        to_model["reverse_m2m"].append(
                            {
                                "name": reverse_name,
                                "source_model": from_model["name"],
                                "source_service": from_model["module_name"],
                                "source_endpoint": f"{from_model['module_name']}s",
                                "label_field": from_model.get("unique_search_field") or from_model["search_field"],
                                "display": to_fk.get("reverse_display", True),
                                "link_model": model["name"],
                                "link_module": model["source_module"],
                                "source_source_module": from_model["source_module"],
                                "source_fk_field": from_fk["name"],
                                "target_fk_field": to_fk["name"],
                                "order_field": model.get("link_order_field"),
                            }
                        )

    theme_config, radius = resolve_theme(site_config)
    generate_file("index.css.j2", {"theme": theme_config, "radius": radius}, cwd / "frontend" / "src" / "index.css")

    # Sync assets BEFORE generating models so that our generated Settings.tsx isn't overwritten
    sync_frontend_assets(cwd, site_config)
    sync_backend_assets(cwd, backend_path, site_config)

    for model in found_models:
        if model["is_link_table"] and not model.get("is_association_table"):
            continue

        context = {"model": model}

        is_system_config = model["module_name"] == "system_config" and model["name"] == "SystemConfig"
        is_custom_config = model["module_name"] == "custom_config" and model["name"] == "CustomConfig"

        if is_system_config or is_custom_config:
            if not model.get("frontend_only"):
                generate_file(
                    "singleton_schema.py.j2",
                    context,
                    backend_path / "app" / "schemas" / f"{model['module_name']}.py",
                )
                generate_file(
                    "singleton_crud.py.j2",
                    context,
                    backend_path / "app" / "cruds" / f"{model['module_name']}.py",
                )
                generate_file(
                    "singleton_service.py.j2",
                    context,
                    backend_path / "app" / "services" / f"{model['module_name']}.py",
                )
                generate_file(
                    "singleton_api.py.j2",
                    context,
                    backend_path / "app" / "api" / "endpoints" / f"{model['module_name']}.py",
                )
                generate_file(
                    "singleton_frontend_service.ts.j2",
                    context,
                    cwd / "frontend" / "src" / "services" / f"{model['module_name']}.ts",
                )

            generate_file(
                "singleton_store.ts.j2",
                context,
                cwd / "frontend" / "src" / "stores" / f"use{model['name']}Store.ts",
            )
            continue

        if model.get("is_singleton"):
            if not model.get("frontend_only"):
                generate_file(
                    "singleton_schema.py.j2",
                    context,
                    backend_path / "app" / "schemas" / f"{model['module_name']}.py",
                )
                generate_file(
                    "singleton_crud.py.j2",
                    context,
                    backend_path / "app" / "cruds" / f"{model['module_name']}.py",
                )
                generate_file(
                    "singleton_service.py.j2",
                    context,
                    backend_path / "app" / "services" / f"{model['module_name']}.py",
                )
                generate_file(
                    "singleton_api.py.j2",
                    context,
                    backend_path / "app" / "api" / "endpoints" / f"{model['module_name']}.py",
                )
                generate_file(
                    "singleton_frontend_service.ts.j2",
                    context,
                    cwd / "frontend" / "src" / "services" / f"{model['module_name']}.ts",
                )

            generate_file(
                "singleton_store.ts.j2",
                context,
                cwd / "frontend" / "src" / "stores" / f"use{model['name']}Store.ts",
            )
            generate_file(
                "singleton_page.tsx.j2",
                context,
                cwd / "frontend" / "src" / "pages" / f"{model['module_name']}" / "index.tsx",
            )
            continue

        is_user_model = model["name"] == "User"

        schema_tpl = "user_schema.py.j2" if is_user_model else "schema.py.j2"
        generate_file(schema_tpl, context, backend_path / "app" / "schemas" / f"{model['module_name']}.py")

        crud_tpl = "user_crud.py.j2" if is_user_model else "crud.py.j2"
        generate_file(crud_tpl, context, backend_path / "app" / "cruds" / f"{model['module_name']}.py")

        service_tpl = "user_service.py.j2" if is_user_model else "service.py.j2"
        generate_file(service_tpl, context, backend_path / "app" / "services" / f"{model['module_name']}.py")

        generate_file("api.py.j2", context, backend_path / "app" / "api" / "endpoints" / f"{model['module_name']}.py")

        generate_file("frontend_service.ts.j2", context, cwd / "frontend" / "src" / "services" / f"{model['module_name']}.ts")

        generate_file(
            "frontend_store.ts.j2",
            context,
            cwd / "frontend" / "src" / "stores" / f"use{model['name']}Store.ts",
        )

        generate_file(
            "frontend_page_list.tsx.j2",
            context,
            cwd / "frontend" / "src" / "pages" / f"{model['module_name']}" / "index.tsx",
        )

        generate_file(
            "frontend_page_detail.tsx.j2",
            context,
            cwd / "frontend" / "src" / "pages" / f"{model['module_name']}" / "detail.tsx",
        )

        # Generate backend tests
        if not model.get("frontend_only"):
            generate_file(
                "backend_test.py.j2",
                context,
                backend_path / "tests" / f"test_{model['module_name']}_api.py",
            )

        # Generate frontend tests (disabled - causes TS build errors)
        # generate_file(
        #     "frontend_test.ts.j2",
        #     context,
        #     cwd / "frontend" / "src" / f"{model['module_name']}.test.ts",
        # )

    api_models = [
        m
        for m in found_models
        if not m.get("frontend_only")
        and (not m["is_link_table"] or (m.get("is_association_table") and m.get("show_in_menu")))
    ]

    nav_order = site_config.get("nav_order", [])
    if isinstance(nav_order, list) and nav_order:
        order_map = {str(x): i for i, x in enumerate(nav_order)}
        api_models.sort(key=lambda m: (order_map.get(m["module_name"], 10_000), m["module_name"]))
    else:
        api_models.sort(key=lambda m: m["module_name"])

    notification_model = next((m for m in found_models if m.get("is_notification_table")), None)
    notifications_enabled = bool(notification_model)
    notifications_api_base = f"/{notification_model['module_name']}s" if notification_model else "/notifications"

    # Always generate WS files for online status tracking
    generate_file("ws.py.j2", {}, backend_path / "app" / "core" / "ws.py")
    generate_file("ws_api.py.j2", {}, backend_path / "app" / "api" / "endpoints" / "ws.py")

    if notification_model:
        names = {f["name"] for f in notification_model.get("fields", [])}
        required = {"title", "summary", "content", "created_at", "is_read", "user_id"}
        missing = sorted([x for x in required if x not in names])
        if missing:
            raise ValueError(
                f"Notification model '{notification_model['name']}' is missing required fields: {', '.join(missing)}"
            )

    # Process scheduled tasks from site_config (must be before update_api_router)
    scheduled_tasks = site_config.get("scheduled_tasks", [])
    update_api_router(api_models, backend_path / "app" / "api" / "api.py", scheduled_tasks)

    if scheduled_tasks:
        # Group tasks by module (extracted from func path like "app.tasks.alarm:daily_summary")
        tasks_by_module: Dict[str, List[dict]] = {}
        for task in scheduled_tasks:
            func_path = task.get("func", "")
            if ":" in func_path:
                module_path = func_path.split(":")[0]  # e.g. "app.tasks.alarm"
                module_name = module_path.split(".")[-1]  # e.g. "alarm"
            else:
                module_name = "default"
                module_path = "app.tasks.default"

            if module_name not in tasks_by_module:
                tasks_by_module[module_name] = []

            tasks_by_module[module_name].append({
                "name": task.get("name", ""),
                "func": func_path,
                "cron": task.get("cron", "0 0 * * *"),
                "description": task.get("description", ""),
                "enabled": task.get("enabled", True),
            })

        # Generate task files for each module
        for module_name, tasks in tasks_by_module.items():
            task_file_path = backend_path / "app" / "tasks" / f"{module_name}.py"
            # Only generate if file doesn't exist (don't overwrite existing user code)
            if not task_file_path.exists():
                generate_file(
                    "app_tasks.py.j2",
                    {"tasks": tasks},
                    task_file_path,
                )
                console.print(f"Generated task file: {module_name}.py")

        # Generate/overwrite tasks __init__.py when there are tasks
        tasks_init = backend_path / "app" / "tasks" / "__init__.py"
        init_content = f"""# Tasks module
# Auto-generated - do not edit manually

"""
        for module_name in tasks_by_module.keys():
            init_content += f"from app.tasks import {module_name}\n"
        tasks_init.write_text(init_content)
        console.print("Updated tasks __init__.py")

    system_model = next((m for m in found_models if m["module_name"] == "system_config" and m["name"] == "SystemConfig"), None)
    custom_model = next((m for m in found_models if m["module_name"] == "custom_config" and m["name"] == "CustomConfig"), None)
    generate_file("settings_page.tsx.j2", {"system_model": system_model, "custom_model": custom_model}, cwd / "frontend" / "src" / "pages" / "Settings.tsx")

    generate_file("frontend_routes.tsx.j2", {"models": api_models}, cwd / "frontend" / "src" / "Routes.tsx")
    generate_file("frontend_menu.tsx.j2", {"models": api_models}, cwd / "frontend" / "src" / "Menu.tsx")
    generate_file("dashboard_page.tsx.j2", {"models": api_models, "scheduled_tasks": scheduled_tasks}, cwd / "frontend" / "src" / "pages" / "Dashboard.tsx")
    generate_file(
        "frontend_features.ts.j2",
        {"notifications_enabled": notifications_enabled, "notifications_api_base": notifications_api_base},
        cwd / "frontend" / "src" / "features.ts",
    )

    # Generate task service and store if scheduled_tasks is configured
    if scheduled_tasks:
        generate_file(
            "frontend_task_service.ts.j2",
            {},
            cwd / "frontend" / "src" / "services" / "tasks.ts",
        )
        generate_file(
            "task_store.ts.j2",
            {},
            cwd / "frontend" / "src" / "stores" / "useTaskStore.ts",
        )

    generate_locale_files(found_models, cwd / "frontend" / "src" / "locales")
