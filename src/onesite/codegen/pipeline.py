"""Code generation pipeline — orchestrates all codegen in discrete phases.

Each phase has a clear responsibility. The phases are executed in order by
generate_code(), which serves as the public entry point.
"""

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

_ROLE_ORDER = ["user", "admin", "developer"]
_ROLE_TO_ENUM = {"user": "USER", "admin": "ADMIN", "developer": "DEVELOPER"}


# ── Helpers ────────────────────────────────────────────────────────────────

def _to_snake(name: str) -> str:
    import re
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _install_snake_case_tablenames() -> None:
    """Monkey-patch SQLModel to auto-generate snake_case table names."""
    if getattr(sqlmodel.main, "_onesite_snake_tablename_installed", False):
        return

    original_new = sqlmodel.main.SQLModelMetaclass.__new__

    def patched_new(mcls, name, bases, dict_, **kwargs):
        if kwargs.get("table", False) and "__tablename__" not in dict_:
            dict_["__tablename__"] = _to_snake(name)
        return original_new(mcls, name, bases, dict_, **kwargs)

    sqlmodel.main.SQLModelMetaclass.__new__ = patched_new
    sqlmodel.main._onesite_snake_tablename_installed = True


def _pluralize(name: str) -> str:
    """Simple English pluralization."""
    if name.endswith("y") and name[-2] not in "aeiou":
        return f"{name[:-1]}ies"
    return f"{name}s"


# ═══════════════════════════════════════════════════════════════════════════
# Phase 1 — Config & Setup
# ═══════════════════════════════════════════════════════════════════════════

def phase_load_config(cwd: Path) -> tuple[dict, Path]:
    """Load site_config.json, set defaults, sync .env files.

    Returns (site_config, backend_path).
    """
    site_config = load_site_config(cwd)

    site_config.setdefault("project_name", "MyApp")
    site_config.setdefault("database_url", "sqlite:///./app.db")
    site_config.setdefault("upload_dir", "uploads")
    site_config.setdefault("secret_key", "changeme")
    site_config.setdefault("access_token_expire_minutes", 11520)
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
    return site_config, backend_path


# ═══════════════════════════════════════════════════════════════════════════
# Phase 2 — Model Sync
# ═══════════════════════════════════════════════════════════════════════════

def phase_sync_models(cwd: Path, backend_path: Path) -> None:
    """Copy model .py files from *project* models/ and *template* models/ into backend."""
    models_src_dir = cwd / "models"
    models_dest_dir = backend_path / "app" / "models"
    template_models_dir = (
        Path(__file__).resolve().parent.parent / "templates" / "models"
    )

    models_dest_dir.mkdir(parents=True, exist_ok=True)
    (models_dest_dir / "__init__.py").touch(exist_ok=True)

    if models_src_dir.exists():
        console.print(
            f"[green]Syncing models from {models_src_dir} to {models_dest_dir}...[/green]"
        )
        for model_file in models_src_dir.glob("*.py"):
            shutil.copy2(model_file, models_dest_dir / model_file.name)
            console.print(f"Synced model: {model_file.name}")

    if template_models_dir.exists():
        for model_file in template_models_dir.glob("*.py"):
            target_in_project = models_src_dir / model_file.name
            if not target_in_project.exists():
                shutil.copy2(model_file, models_dest_dir / model_file.name)
                console.print(
                    f"Synced base model from template: {model_file.name}"
                )
            else:
                console.print(
                    f"Skipping template model {model_file.name} (overridden in project)"
                )


# ═══════════════════════════════════════════════════════════════════════════
# Phase 3 — Introspection
# ═══════════════════════════════════════════════════════════════════════════

def _ensure_user_password_field(fields: list[dict]) -> None:
    """Append a default password field to the User model if it lacks one."""
    has_password = any(f["name"] == "password" for f in fields)
    if has_password:
        return

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


def _build_model_dict(
    name: str,
    module_name: str,
    source_module: str,
    fields: list[dict],
    foreign_keys: list[dict],
    search_field: str | None,
    unique_search_field: str | None,
    is_link_table: bool,
    is_singleton: bool,
    model_permissions: str,
    role_permissions: dict,
    role_visible: bool,
    special_me_permissions: bool,
    frontend_only: bool,
    translations: dict,
    auto_refresh: bool,
    refresh_interval: int,
    reverse_fk_display: bool,
    model_site_props: dict,
    actions: list[dict],
    is_notification_table: bool,
    union_key: str | None,
    importable: bool,
    exportable: bool,
    import_key: str | None,
    owner_field: str | None = None,
    page_edit: bool = False,
) -> dict:
    """Assemble the canonical model metadata dict from introspection results."""
    schema_imports = sorted({imp for f in fields for imp in f.get("py_imports", [])})
    return {
        "name": name,
        "module_name": module_name,
        "source_module": source_module,
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
        "has_created_at": any(f["name"] == "created_at" for f in fields),
        "owner_field": owner_field,
        "page_edit": page_edit,
    }


def phase_introspect(backend_path: Path) -> list[dict]:
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
    module_names = [f.stem for f in models_dir.glob("*.py") if f.stem != "__init__"]
    found_models: list[dict] = []

    for module_name in module_names:
        full_module_name = f"app.models.{module_name}"
        try:
            if full_module_name in sys.modules:
                module = importlib.reload(sys.modules[full_module_name])
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


def _introspect_module(module: Any, module_name: str, full_module_name: str) -> list[dict] | None:
    """Introspect a single model module and return model metadata dicts."""
    results: list[dict] = []

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


def _process_introspected_class(
    obj: type, name: str, module_name: str, full_module_name: str
) -> dict | None:
    """Run get_model_fields on a single class and build its metadata dict."""
    model_module_name = _to_snake(name)
    (
        fields, foreign_keys, search_field, unique_search_field,
        is_link_table, is_singleton, model_permissions, frontend_only,
        translations, auto_refresh, refresh_interval, reverse_fk_display,
        model_site_props, actions, is_notification_table, union_key,
        importable, exportable, import_key, role_permissions,
        role_visible, special_me_permissions, owner_field,
        page_edit,
    ) = get_model_fields(obj, model_module_name)

    if name == "User":
        _ensure_user_password_field(fields)

    # Validate importable models have an import_key
    if importable:
        if import_key:
            pass  # use configured key
        elif any(f["name"] == "title" and f.get("is_unique") for f in fields):
            import_key = "title"
        else:
            console.print(
                f"[red]Error: Model '{name}' has importable=True but no import_key configured.[/red]"
            )
            console.print(
                "[red]Please set __onesite__ = {'import_key': 'field_name'} "
                "or ensure 'title' field has unique=True[/red]"
            )
            return None

    return _build_model_dict(
        name, model_module_name, module_name,
        fields, foreign_keys, search_field, unique_search_field,
        is_link_table, is_singleton, model_permissions, role_permissions,
        role_visible, special_me_permissions, frontend_only, translations,
        auto_refresh, refresh_interval, reverse_fk_display, model_site_props,
        actions, is_notification_table, union_key, importable, exportable,
        import_key, owner_field, page_edit,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Phase 4 — Relationship Resolution
# ═══════════════════════════════════════════════════════════════════════════

def _resolve_min_roles(models: list[dict]) -> None:
    """Compute the minimum role level required for each CRUD operation."""

    def _min_role_for(perm_char: str, role_permissions: dict) -> str:
        for role in _ROLE_ORDER:
            perms = role_permissions.get(role, "")
            if perm_char in perms:
                return _ROLE_TO_ENUM[role]
        return "DEVELOPER"

    for model in models:
        rp = model.get("role_permissions", {})
        model["min_role_for_read"] = _min_role_for("r", rp)
        model["min_role_for_create"] = _min_role_for("c", rp)
        model["min_role_for_update"] = _min_role_for("u", rp)
        model["min_role_for_delete"] = _min_role_for("d", rp)


def _init_link_table_flags(models: list[dict]) -> None:
    """Set link-table-related fields and show_in_menu for every model."""
    for model in models:
        model.setdefault("m2m_fields", [])
        model.setdefault("reverse_m2m", [])
        model["reverse_foreign_keys"] = []

        if model.get("is_link_table"):
            order_field = next(
                (f for f in model["fields"] if f["name"] == "order" and not f.get("fk_info")),
                None,
            )
            model["link_order_field"] = "order" if order_field else None

            link_extra_fields = [
                f for f in model["fields"]
                if not f.get("fk_info") and f["name"] not in ("id", "order")
            ]
            model["link_extra_fields"] = link_extra_fields
            model["is_association_table"] = len(link_extra_fields) > 0
        else:
            model["link_order_field"] = None
            model["link_extra_fields"] = []
            model["is_association_table"] = False

        # Validate owner_field: must be an FK field pointing to User
        owner_field = model.get("owner_field")
        if owner_field:
            fk_names = {fk["name"] for fk in model["foreign_keys"]}
            if owner_field not in fk_names:
                console.print(
                    f"[yellow]Warning: Model '{model['name']}' has owner_field='{owner_field}' "
                    f"but no matching FK field found. Owner filtering disabled.[/yellow]"
                )
                model["owner_field"] = None
            else:
                # Verify the FK targets the User model
                fk = next((fk for fk in model["foreign_keys"] if fk["name"] == owner_field), None)
                if fk and fk["target_model"] != "User":
                    console.print(
                        f"[yellow]Warning: Model '{model['name']}' owner_field='{owner_field}' "
                        f"targets '{fk['target_model']}', not 'User'. Owner filtering disabled.[/yellow]"
                    )
                    model["owner_field"] = None

        if model.get("is_link_table") and model.get("is_association_table"):
            model["show_in_menu"] = bool(
                model.get("site_props", {}).get("show_in_menu", True)
            )
        else:
            model["show_in_menu"] = True


def _resolve_fk_labels_and_reverse(models: list[dict], model_map: dict) -> None:
    """Label FK targets and populate reverse_foreign_keys on target models."""
    for model in models:
        for fk in model["foreign_keys"]:
            target_model = model_map.get(fk["target_model"])
            if target_model is None:
                continue

            fk["label_field"] = (
                target_model.get("unique_search_field") or target_model["search_field"]
            )
            fk["target_readable_fields"] = [
                f for f in target_model["fields"]
                if "r" in f["permissions"]
                and f["name"] != "password"
                and not f.get("fk_info")
            ]

            if model.get("is_link_table"):
                continue

            reverse_name = _pluralize(model["module_name"])
            target_model["reverse_foreign_keys"].append({
                "name": reverse_name,
                "source_model": model["name"],
                "source_service": model["module_name"],
                "source_fk_field": fk["name"],
                "label_field": model.get("unique_search_field") or model["search_field"],
                "display": fk.get("reverse_display", True),
            })


def _resolve_m2m(models: list[dict], model_map: dict, module_map: dict) -> None:
    """Resolve many-to-many relationships through link tables."""
    for model in models:
        if not model.get("is_link_table"):
            continue

        fks = model["foreign_keys"]
        if len(fks) < 2:
            continue

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

        editable_edges = {
            (str(d.get("from", "")), str(d.get("to", "")))
            for d in directions
            if isinstance(d, dict) and d.get("editable", True)
        }

        for d in directions:
            _apply_m2m_direction(d, model, fks, models, model_map, module_map, editable_edges)


def _apply_m2m_direction(
    d: Any,
    link_model: dict,
    link_fks: list[dict],
    all_models: list[dict],
    model_map: dict,
    module_map: dict,
    editable_edges: set,
) -> None:
    """Apply a single M2M direction config (one edge in the link table graph)."""
    if not isinstance(d, dict):
        return

    from_ref = str(d.get("from", "")).strip()
    to_ref = str(d.get("to", "")).strip()
    if not from_ref or not to_ref:
        return

    from_model = module_map.get(from_ref) or model_map.get(from_ref)
    to_model = module_map.get(to_ref) or model_map.get(to_ref)
    if not from_model or not to_model:
        return

    def _find_fk_for(target_service: str, target_model: str):
        return next(
            (
                fk for fk in link_fks
                if fk.get("target_service") == target_service
                or fk.get("target_model") == target_model
            ),
            None,
        )

    from_fk = _find_fk_for(from_model["module_name"], from_model["name"])
    to_fk = _find_fk_for(to_model["module_name"], to_model["name"])
    if not from_fk or not to_fk:
        return

    # Forward direction: add m2m_field to from_model
    if d.get("editable", True):
        m2m_field_name = f"{to_model['lower_name']}_ids"
        existing = next(
            (
                x for x in from_model.get("m2m_fields", [])
                if x.get("name") == m2m_field_name
                and x.get("target_model") == to_model["name"]
            ),
            None,
        )
        if existing is None:
            from_model["m2m_fields"].append({
                "name": m2m_field_name,
                "target_model": to_model["name"],
                "target_service": to_model["module_name"],
                "target_endpoint": f"{to_model['module_name']}s",
                "label_field": (
                    to_model.get("unique_search_field") or to_model["search_field"]
                ),
                "link_model": link_model["name"],
                "link_module": link_model["source_module"],
                "target_source_module": to_model["source_module"],
                "source_fk_field": from_fk["name"],
                "target_fk_field": to_fk["name"],
                "order_field": link_model.get("link_order_field"),
            })

    # Skip reverse if this edge was explicitly configured as non-reversible
    if (to_model["module_name"], from_model["module_name"]) in editable_edges:
        return

    reverse_name = _pluralize(from_model["module_name"])
    existing_reverse = next(
        (
            x for x in to_model.get("reverse_m2m", [])
            if x.get("name") == reverse_name
            and x.get("source_model") == from_model["name"]
        ),
        None,
    )
    if existing_reverse is None:
        to_model["reverse_m2m"].append({
            "name": reverse_name,
            "source_model": from_model["name"],
            "source_service": from_model["module_name"],
            "source_endpoint": f"{from_model['module_name']}s",
            "label_field": (
                from_model.get("unique_search_field") or from_model["search_field"]
            ),
            "display": to_fk.get("reverse_display", True),
            "link_model": link_model["name"],
            "link_module": link_model["source_module"],
            "source_source_module": from_model["source_module"],
            "source_fk_field": from_fk["name"],
            "target_fk_field": to_fk["name"],
            "order_field": link_model.get("link_order_field"),
        })


def phase_resolve_relationships(models: list[dict]) -> list[dict]:
    """Resolve FK labels, reverse FK, and M2M relationships across all models.

    Mutates the model dicts in place (adding relation containers, computed fields),
    then returns the same list for convenience.
    """
    model_map = {m["name"]: m for m in models}
    module_map = {m["module_name"]: m for m in models}

    _resolve_min_roles(models)
    _init_link_table_flags(models)
    _resolve_fk_labels_and_reverse(models, model_map)
    _resolve_m2m(models, model_map, module_map)

    return models


# ═══════════════════════════════════════════════════════════════════════════
# Phase 5 — Theme & Assets
# ═══════════════════════════════════════════════════════════════════════════

def phase_theme_and_assets(site_config: dict, cwd: Path, backend_path: Path) -> None:
    """Generate theme CSS and sync frontend / backend static assets.

    Must run *before* per-model generation so that generated files like
    Settings.tsx are not overwritten by the asset sync.
    """
    theme_config, radius = resolve_theme(site_config)
    generate_file(
        "index.css.j2",
        {"theme": theme_config, "radius": radius},
        cwd / "frontend" / "src" / "index.css",
    )
    sync_frontend_assets(cwd, site_config)
    sync_backend_assets(cwd, backend_path, site_config)


# ═══════════════════════════════════════════════════════════════════════════
# Phase 6 — Per-Model Code Generation
# ═══════════════════════════════════════════════════════════════════════════

def _generate_singleton(model: dict, cwd: Path, backend_path: Path) -> None:
    """Generate code for singleton / config models."""
    context = {"model": model}
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


def _backend_path(tpl: str, model: dict, backend_path: Path) -> Path:
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


def _generate_regular_model(model: dict, cwd: Path, backend_path: Path) -> None:
    """Generate code for a regular (non-singleton, non-link) model."""
    context = {"model": model}
    is_user_model = model["name"] == "User"

    tpl_schema = "user_schema.py.j2" if is_user_model else "schema.py.j2"
    tpl_crud = "user_crud.py.j2" if is_user_model else "crud.py.j2"
    tpl_service = "user_service.py.j2" if is_user_model else "service.py.j2"

    generate_file(tpl_schema, context, _backend_path(tpl_schema, model, backend_path))
    generate_file(tpl_crud, context, _backend_path(tpl_crud, model, backend_path))
    generate_file(tpl_service, context, _backend_path(tpl_service, model, backend_path))
    generate_file("api.py.j2", context, _backend_path("api.py.j2", model, backend_path))

    generate_file(
        "frontend_service.ts.j2", context,
        cwd / "frontend" / "src" / "services" / f"{model['module_name']}.ts",
    )
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


def _sort_api_models(api_models: list[dict], site_config: dict) -> list[dict]:
    """Apply nav_order sorting from site_config, falling back to alphabetical."""
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
    models: list[dict], site_config: dict, cwd: Path, backend_path: Path
) -> list[dict]:
    """Generate per-model files (schemas, cruds, services, APIs, frontend).

    Returns the sorted list of API-visible models for use in routing & navigation.
    """
    for model in models:
        if model["is_link_table"] and not model.get("is_association_table"):
            continue

        if model.get("is_singleton") or (
            model["module_name"] == "system_config" and model["name"] == "SystemConfig"
        ) or (
            model["module_name"] == "custom_config" and model["name"] == "CustomConfig"
        ):
            _generate_singleton(model, cwd, backend_path)
        else:
            _generate_regular_model(model, cwd, backend_path)

    api_models = [
        m for m in models
        if not m.get("frontend_only")
        and (not m["is_link_table"] or (m.get("is_association_table") and m.get("show_in_menu")))
    ]
    return _sort_api_models(api_models, site_config)


# ═══════════════════════════════════════════════════════════════════════════
# Phase 7 — Aggregated Generation
# ═══════════════════════════════════════════════════════════════════════════

def _validate_notification_model(models: list[dict]) -> tuple[bool, str]:
    """Check notification model requirements; return (enabled, api_base)."""
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
    models: list[dict],
    api_models: list[dict],
    site_config: dict,
    cwd: Path,
    backend_path: Path,
) -> None:
    """Generate cross-cutting files: router, routes, menu, dashboard, i18n, etc."""
    # ── Notification model lookup & WS (order preserved from original) ──
    notifications_enabled, notifications_api_base = _validate_notification_model(models)

    generate_file("ws.py.j2", {}, backend_path / "app" / "core" / "ws.py")
    generate_file("ws_api.py.j2", {}, backend_path / "app" / "api" / "endpoints" / "ws.py")

    # ── API router ──
    scheduled_tasks = site_config.get("scheduled_tasks", [])
    update_api_router(api_models, backend_path / "app" / "api" / "api.py", scheduled_tasks)

    # ── Settings page ──
    system_model = next(
        (m for m in models
         if m["module_name"] == "system_config" and m["name"] == "SystemConfig"),
        None,
    )
    custom_model = next(
        (m for m in models
         if m["module_name"] == "custom_config" and m["name"] == "CustomConfig"),
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
    generate_file(
        "frontend_routes.tsx.j2", {"models": api_models},
        cwd / "frontend" / "src" / "Routes.tsx",
    )
    generate_file(
        "frontend_menu.tsx.j2", {"models": api_models},
        cwd / "frontend" / "src" / "Menu.tsx",
    )
    generate_file(
        "dashboard_page.tsx.j2",
        {"models": api_models, "scheduled_tasks": scheduled_tasks},
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


# ═══════════════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════════════

def generate_code() -> None:
    """Load configuration, introspect models, and generate the full project.

    This is the public entry point called by ``site sync``.
    """
    cwd = Path(os.getcwd())

    # Phase 1 — Config
    if not (cwd / "backend").exists():
        console.print("[red]Backend directory not found. Are you in the project root?[/red]")
        return
    site_config, backend_path = phase_load_config(cwd)

    # Phase 2 — Model files
    phase_sync_models(cwd, backend_path)

    # Phase 3 — Introspect
    models = phase_introspect(backend_path)
    if not models:
        return

    # Phase 4 — Relationships
    phase_resolve_relationships(models)

    # Phase 5 — Theme & assets (before codegen so generated files aren't overwritten)
    phase_theme_and_assets(site_config, cwd, backend_path)

    # Phase 6 — Per-model code
    api_models = phase_generate_per_model(models, site_config, cwd, backend_path)

    # Phase 7 — Aggregated code
    phase_generate_aggregated(models, api_models, site_config, cwd, backend_path)
