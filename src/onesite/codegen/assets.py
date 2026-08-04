import ast
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from rich.console import Console

from ..project_paths import get_project_paths
from .config import SiteConfigError
from .file_utils import copy_file_with_status, write_file_with_status
from .render import generate_file
from .theme import resolve_theme

console = Console()


THEME_FRONTEND_DEPENDENCIES: Dict[str, Dict[str, str]] = {
    "normal": {"antd": "^6.5.1"},
}


def _sync_frontend_theme_assets(
    template_root: Path,
    target_frontend_root: Path,
    site_config: Dict[str, Any],
) -> None:
    """Overlay build-time theme assets and add their npm dependencies."""
    theme_name = resolve_theme(site_config)[0]["id"]
    theme_root = template_root / "themes" / theme_name
    if theme_root.is_dir():
        for source in theme_root.rglob("*"):
            if source.is_file():
                copy_file_with_status(
                    source,
                    target_frontend_root / source.relative_to(theme_root),
                )

    dependencies = THEME_FRONTEND_DEPENDENCIES.get(theme_name, {})
    if not dependencies:
        return
    package_path = target_frontend_root / "package.json"
    package_data = json.loads(package_path.read_text(encoding="utf-8"))
    package_dependencies = package_data.setdefault("dependencies", {})
    package_dependencies.update(dependencies)
    package_data["dependencies"] = dict(sorted(package_dependencies.items()))
    write_file_with_status(
        package_path,
        json.dumps(package_data, ensure_ascii=False, indent=2) + "\n",
    )


def _sync_desktop_assets(target_frontend_root: Path, site_config: Dict[str, Any]) -> None:
    """Generate the Tauri 2 shell used by current-platform desktop builds."""
    template_root = Path(__file__).resolve().parent.parent / "templates" / "desktop"
    target_root = target_frontend_root / "src-tauri"

    for source in template_root.rglob("*"):
        if source.is_file():
            copy_file_with_status(source, target_root / source.relative_to(template_root))

    desktop = dict(site_config["desktop"])
    crate_name = re.sub(
        r"[^a-z0-9_]+",
        "_",
        str(site_config.get("project_name", "onesite")).lower().replace("-", "_"),
    ).strip("_")
    if not crate_name:
        crate_name = "onesite_app"
    if crate_name[0].isdigit():
        crate_name = f"app_{crate_name}"
    desktop["crate_name"] = crate_name
    context = {"config": site_config, "desktop": desktop}
    generate_file("desktop_Cargo.toml.j2", context, target_root / "Cargo.toml")
    generate_file(
        "desktop_tauri.conf.json.j2", context, target_root / "tauri.conf.json"
    )


def _ensure_init_py(dir_path: Path) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    init_file = dir_path / "__init__.py"
    if not init_file.exists():
        write_file_with_status(init_file, "")


def _async_function_exists(file_path: Path, func_name: str) -> bool:
    """Return whether a module defines the named top-level async function."""
    if not file_path.exists():
        return False
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeError):
        return False
    return any(
        isinstance(node, ast.AsyncFunctionDef) and node.name == func_name
        for node in tree.body
    )


def _validate_async_function_signature(
    file_path: Path,
    func_name: str,
    expected_parameters: set[str],
    allow_missing_context: bool = False,
) -> None:
    """Require a top-level async handler with the configured named inputs."""
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeError) as exc:
        raise SiteConfigError(f"Unable to parse {file_path}: {exc}") from exc
    function = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == func_name
        ),
        None,
    )
    if function is None:
        raise SiteConfigError(
            f"{file_path} must define a top-level async function named {func_name!r}."
        )
    if function.args.vararg or function.args.kwarg or function.args.posonlyargs:
        raise SiteConfigError(
            f"{file_path}:{func_name} must use explicit named parameters."
        )
    actual = {
        argument.arg
        for argument in [*function.args.args, *function.args.kwonlyargs]
    }
    allowed = [expected_parameters]
    if allow_missing_context:
        allowed.append(expected_parameters - {"context"})
    if actual not in allowed:
        missing = sorted(expected_parameters - actual)
        unexpected = sorted(actual - expected_parameters)
        details = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected {', '.join(unexpected)}")
        raise SiteConfigError(
            f"{file_path}:{func_name} parameters do not match configured inputs "
            f"({'; '.join(details)})."
        )


def _mirror_python_tree(source: Path, destination: Path) -> None:
    """Mirror Python source files without treating the generated copy as source."""
    destination.mkdir(parents=True, exist_ok=True)
    desired = {
        path.relative_to(source): path
        for path in source.rglob("*.py")
        if path.is_file()
    }

    for existing in sorted(destination.rglob("*.py")):
        relative = existing.relative_to(destination)
        if relative not in desired:
            existing.unlink()
            console.print(
                f"[yellow]Removed stale generated MQTT source {existing}[/yellow]"
            )

    for relative, source_file in sorted(desired.items()):
        copy_file_with_status(source_file, destination / relative)


def _mirror_source_tree(source: Path, destination: Path, label: str) -> None:
    """Mirror a developer-owned source tree into generated backend output."""
    desired = {}
    if source.exists():
        desired = {
            path.relative_to(source): path
            for path in source.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
        }

    if destination.exists():
        for existing in sorted(
            (path for path in destination.rglob("*") if path.is_file()),
            reverse=True,
        ):
            relative = existing.relative_to(destination)
            if relative not in desired:
                existing.unlink()
                console.print(
                    f"[yellow]Removed stale generated {label} file {existing}[/yellow]"
                )

        for directory in sorted(
            (path for path in destination.rglob("*") if path.is_dir()),
            reverse=True,
        ):
            if not any(directory.iterdir()):
                directory.rmdir()

    for relative, source_file in sorted(desired.items()):
        copy_file_with_status(source_file, destination / relative)


def _sync_project_utils(cwd: Path, backend_path: Path) -> None:
    """Sync the project's ``utils`` package into the generated backend."""
    paths = get_project_paths(cwd)
    source_utils = paths.source / "utils"
    target_utils = backend_path / "app" / "utils"

    if source_utils.exists():
        _ensure_init_py(source_utils)
    _mirror_source_tree(source_utils, target_utils, "utils")


def _sync_mqtt_callbacks(
    cwd: Path,
    backend_path: Path,
    callbacks: List[Dict[str, Any]],
) -> None:
    """Scaffold project MQTT handlers and mirror them into the backend."""
    source_integrations = get_project_paths(cwd).integrations
    source_mqtt = source_integrations / "mqtt"
    target_integrations = backend_path / "app" / "integrations"
    target_mqtt = target_integrations / "mqtt"
    legacy_mqtt = backend_path / "app" / "consumers" / "mqtt"

    _ensure_init_py(source_integrations)
    _ensure_init_py(source_mqtt)

    for callback in callbacks:
        handler_name = callback["handler"]
        source_file = source_mqtt / f"{handler_name}.py"

        if not source_file.exists():
            legacy_file = legacy_mqtt / f"{handler_name}.py"
            if _async_function_exists(legacy_file, handler_name):
                copy_file_with_status(legacy_file, source_file)
                console.print(
                    f"[yellow]Migrated legacy MQTT handler to {source_file}[/yellow]"
                )
            else:
                generate_file(
                    "mqtt_callback.py.j2",
                    {"callback": callback},
                    source_file,
                )

        if not _async_function_exists(source_file, handler_name):
            raise SiteConfigError(
                f"{source_file} must define a top-level async function named "
                f"{handler_name!r}."
            )

    copy_file_with_status(
        source_integrations / "__init__.py",
        target_integrations / "__init__.py",
    )
    _mirror_python_tree(source_mqtt, target_mqtt)
    generate_file(
        "mqtt_bindings.py.j2",
        {
            "callbacks": callbacks,
            "handlers": sorted({callback["handler"] for callback in callbacks}),
        },
        backend_path / "app" / "core" / "mqtt_bindings.py",
    )


def _sync_tools(cwd: Path, backend_path: Path, tools: List[Dict[str, Any]]) -> None:
    """Scaffold developer-owned tool handlers and mirror them into backend."""
    source_tools = get_project_paths(cwd).tools
    target_tools = backend_path / "app" / "tools"
    _ensure_init_py(source_tools)

    for tool in tools:
        handler_name = tool["handler"]
        source_file = source_tools / f"{handler_name}.py"
        if not source_file.exists():
            generate_file("tool_handler.py.j2", {"tool": tool}, source_file)
        _validate_async_function_signature(
            source_file,
            handler_name,
            {input_config["name"] for input_config in tool.get("inputs", [])}
            | {"context"},
        )

    _mirror_python_tree(source_tools, target_tools)


def _strip_legacy_task_registration(file_path: Path) -> None:
    """Remove generator-owned registry boilerplate from a task source file.

    Older OneSite versions placed both the handler and a top-level
    ``task_registry.register(...)`` call in the generated task module. Once
    that module becomes developer-owned, only the handler belongs there;
    registration is generated separately in ``scheduled_task_bindings.py``.
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError, UnicodeError):
        return

    lines = source.splitlines(keepends=True)
    removals: list[tuple[int, int]] = []
    for node in tree.body:
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "app.core.scheduler"
            and len(node.names) == 1
            and node.names[0].name == "task_registry"
        ):
            removals.append((node.lineno - 1, node.end_lineno or node.lineno))
            continue
        if not (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == "register"
            and isinstance(node.value.func.value, ast.Name)
            and node.value.func.value.id == "task_registry"
        ):
            continue
        start = node.lineno - 1
        end = node.end_lineno or node.lineno
        while start > 0 and not lines[start - 1].strip():
            start -= 1
        if start > 0:
            comment = lines[start - 1].strip().lower()
            if comment.startswith("#") and (
                "注册" in comment or "register" in comment or "registration" in comment
            ):
                start -= 1
        removals.append((start, end))

    if not removals:
        return
    removed_lines = {
        index
        for start, end in removals
        for index in range(start, end)
    }
    cleaned = "".join(
        line for index, line in enumerate(lines) if index not in removed_lines
    ).rstrip() + "\n"
    write_file_with_status(file_path, cleaned)


def _sync_scheduled_tasks(
    cwd: Path,
    backend_path: Path,
    tasks: List[Dict[str, Any]],
) -> None:
    """Scaffold developer-owned scheduled task handlers and mirror them."""
    source_tasks = get_project_paths(cwd).tasks
    target_tasks = backend_path / "app" / "tasks"
    _ensure_init_py(source_tasks)

    for task in tasks:
        handler_name = task["handler"]
        source_file = source_tasks / f"{handler_name}.py"
        legacy_file = target_tasks / f"{handler_name}.py"
        if not source_file.exists():
            if _async_function_exists(legacy_file, handler_name):
                copy_file_with_status(legacy_file, source_file)
                console.print(
                    f"[yellow]Migrated generated task handler to {source_file}[/yellow]"
                )
            else:
                generate_file("scheduled_task_handler.py.j2", {"task": task}, source_file)
        _strip_legacy_task_registration(source_file)
        _validate_async_function_signature(
            source_file,
            handler_name,
            set(task.get("params", {})) | {"context"},
            allow_missing_context=True,
        )

    _mirror_python_tree(source_tasks, target_tasks)


def sync_frontend_assets(cwd: Path, site_config: Dict[str, Any]):
    template_root = Path(__file__).resolve().parent.parent / "templates" / "frontend"
    target_frontend_root = get_project_paths(cwd).frontend

    template_components_dir = template_root / "src" / "components" / "ui"
    target_components_dir = target_frontend_root / "src" / "components" / "ui"
    if template_components_dir.exists():
        for item in template_components_dir.glob("*"):
            if item.is_file():
                copy_file_with_status(item, target_components_dir / item.name)

    template_utils_dir = template_root / "src" / "utils"
    target_utils_dir = target_frontend_root / "src" / "utils"
    if template_utils_dir.exists():
        for item in template_utils_dir.glob("*"):
            if item.is_file():
                copy_file_with_status(item, target_utils_dir / item.name)

    template_lib_dir = template_root / "src" / "lib"
    target_lib_dir = target_frontend_root / "src" / "lib"
    if template_lib_dir.exists():
        for item in template_lib_dir.glob("*"):
            if item.is_file():
                copy_file_with_status(item, target_lib_dir / item.name)

    config_files: List[str] = [
        "package.json",
        "tailwind.config.js",
        "postcss.config.js",
        "tsconfig.json",
        "tsconfig.node.json",
        "vite.config.ts",
        "src/main.tsx",
        "src/App.tsx",
        "index.html",
        "src/components/ui/button.tsx",
        "src/components/ui/input.tsx",
        "src/components/ui/label.tsx",
        "src/components/ui/modal.tsx",
        "src/components/ui/table.tsx",
        "src/components/ui/badge.tsx",
        "src/components/ui/switch.tsx",
        "src/components/ui/select.tsx",
        "src/components/ui/card.tsx",
        "src/components/ui/separator.tsx",
        "src/components/ui/image-upload.tsx",
        "src/components/ui/images-upload.tsx",
        "src/components/ui/file-upload.tsx",
        "src/components/ui/file-preview.tsx",
        "src/components/Layout.tsx",
        "src/utils/request.ts",
        "src/pages/Login.tsx",
        "src/pages/ErrorPage.tsx",
        # Profile.tsx is generated via codegen/profile.tsx.j2 in pipeline.py
        "src/components/ui/link-table-ordered-select.tsx",
        "src/components/ui/avatar-fallback.tsx",
        "src/components/notification-bell.tsx",
        "src/services/notification-center.ts",
        "src/vite-env.d.ts",
        "src/i18n.ts",
    ]

    # Only sync Settings.tsx if there is no singleton model generated
    settings_file = target_frontend_root / "src" / "pages" / "Settings.tsx"
    if not settings_file.exists():
        config_files.append("src/pages/Settings.tsx")

    for config_file in config_files:
        if config_file == "vite.config.ts":
            generate_file("frontend_vite.config.ts.j2", {"config": site_config}, target_frontend_root / config_file)
            continue

        if config_file == "index.html":
            generate_file("frontend_index.html.j2", {"config": site_config}, target_frontend_root / config_file)
            continue

        src = template_root / config_file
        dst = target_frontend_root / config_file
        if src.exists():
            copy_file_with_status(src, dst)

    # Theme assets intentionally run last so a build-time theme can replace
    # shared UI adapters and entry points without duplicating page templates.
    _sync_frontend_theme_assets(template_root, target_frontend_root, site_config)

    generate_file("frontend_nginx.conf.j2", {"config": site_config}, target_frontend_root / "nginx.template.conf")

    # Sync runtime config files for container startup
    template_config_js = template_root / "config.js.template"
    if template_config_js.exists():
        copy_file_with_status(template_config_js, target_frontend_root / "config.js.template")
        # Also generate config.js with default values for local development
        config_js_content = """// Runtime configuration - defaults for local development
window.__ENV__ = {
  DOMAIN: window.location.origin,
  API_URL: '/api/v1',
  NODE_ENV: 'development',
  BUILD_VERSION: 'local',
  TIMEZONE: '{{ timezone }}',
};
""".replace("{{ timezone }}", str(site_config.get("extra", {}).get("TIMEZONE", "Asia/Shanghai")))
        write_file_with_status(target_frontend_root / "config.js", config_js_content)

    template_env_sh = template_root / "entrypoint.sh"
    if template_env_sh.exists():
        copy_file_with_status(template_env_sh, target_frontend_root / "entrypoint.sh")

    template_frontend_dockerfile = template_root / "Dockerfile"
    target_frontend_dockerfile = target_frontend_root / "Dockerfile"
    if template_frontend_dockerfile.exists():
        copy_file_with_status(template_frontend_dockerfile, target_frontend_dockerfile)

    template_frontend_dockerignore = template_root / ".dockerignore"
    target_frontend_dockerignore = target_frontend_root / ".dockerignore"
    if template_frontend_dockerignore.exists():
        copy_file_with_status(
            template_frontend_dockerignore,
            target_frontend_dockerignore,
        )

    _sync_desktop_assets(target_frontend_root, site_config)


def sync_backend_assets(cwd: Path, backend_path: Path, site_config: Dict[str, Any]):
    template_backend_root = Path(__file__).resolve().parent.parent / "templates" / "backend"

    _ensure_init_py(backend_path / "app")
    _ensure_init_py(backend_path / "app" / "api")
    _ensure_init_py(backend_path / "app" / "api" / "endpoints")
    _ensure_init_py(backend_path / "app" / "core")
    _ensure_init_py(backend_path / "app" / "cruds")
    _ensure_init_py(backend_path / "app" / "schemas")
    _ensure_init_py(backend_path / "app" / "services")
    _ensure_init_py(backend_path / "app" / "consumers")
    _ensure_init_py(backend_path / "app" / "tasks")

    error_handlers = template_backend_root / "app" / "core" / "error_handlers.py"
    copy_file_with_status(
        error_handlers, backend_path / "app" / "core" / "error_handlers.py"
    )
    _sync_project_utils(cwd, backend_path)
    if site_config.get("tools"):
        _sync_tools(cwd, backend_path, site_config["tools"])
    if site_config.get("scheduled_tasks"):
        _sync_scheduled_tasks(cwd, backend_path, site_config["scheduled_tasks"])

    template_endpoints_dir = template_backend_root / "app" / "api" / "endpoints"
    target_endpoints_dir = backend_path / "app" / "api" / "endpoints"
    if template_endpoints_dir.exists():
        target_endpoints_dir.mkdir(parents=True, exist_ok=True)
        generate_file("backend_api_upload.py.j2", {"config": site_config}, target_endpoints_dir / "upload.py")
        login_py = template_endpoints_dir / "login.py"
        if login_py.exists():
            copy_file_with_status(login_py, target_endpoints_dir / "login.py")

    generate_file("backend_config.py.j2", {"config": site_config}, backend_path / "app" / "core" / "config.py")
    generate_file("backend_datetime.py.j2", {}, backend_path / "app" / "core" / "datetime.py")
    generate_file("backend_main.py.j2", {"config": site_config}, backend_path / "app" / "main.py")

    # Always sync scheduler (no user-edited code, purely infra)
    generate_file("scheduler.py.j2", {}, backend_path / "app" / "core" / "scheduler.py")

    if site_config.get("redis"):
        generate_file("redis.py.j2", {"redis": site_config["redis"]}, backend_path / "app" / "core" / "redis.py")

    if site_config.get("rabbitmq"):
        generate_file("rabbitmq.py.j2", {"rabbitmq": site_config["rabbitmq"]},
                      backend_path / "app" / "core" / "rabbitmq.py")
        # Generate an example consumer
        consumer_init = backend_path / "app" / "consumers" / "__init__.py"
        if not consumer_init.exists() or consumer_init.read_text(encoding="utf-8").strip() == "":
            write_file_with_status(consumer_init, "from . import example\n")

        example_consumer = backend_path / "app" / "consumers" / "example.py"
        if not example_consumer.exists():
            generate_file("consumer_example.py.j2", {}, example_consumer)

    if site_config.get("mqtt"):
        mqtt_config = site_config["mqtt"]
        generate_file("mqtt.py.j2", {"mqtt": mqtt_config},
                      backend_path / "app" / "core" / "mqtt.py")

        callbacks = mqtt_config.get("callbacks", [])
        if callbacks:
            _sync_mqtt_callbacks(cwd, backend_path, callbacks)

    for name in ["logger.py", "security.py", "deps.py", "tablenames.py", "model_hooks.py"]:
        src = template_backend_root / "app" / "core" / name
        dst = backend_path / "app" / "core" / name
        if src.exists():
            copy_file_with_status(src, dst)

    if "ttl_set" in site_config.get("plugins", []):
        ttl_src = template_backend_root / "app" / "core" / "ttl_set.py"
        ttl_dst = backend_path / "app" / "core" / "ttl_set.py"
        if ttl_src.exists():
            copy_file_with_status(ttl_src, ttl_dst)

    if "site_logger" in site_config.get("plugins", []):
        sl_src = template_backend_root / "app" / "core" / "site_logger.py"
        sl_dst = backend_path / "app" / "core" / "site_logger.py"
        if sl_src.exists():
            copy_file_with_status(sl_src, sl_dst)

    initial_data_src = template_backend_root / "app" / "initial_data.py"
    initial_data_dst = backend_path / "app" / "initial_data.py"
    if initial_data_src.exists():
        copy_file_with_status(initial_data_src, initial_data_dst)

    template_requirements = template_backend_root / "requirements.txt"
    target_requirements = backend_path / "requirements.txt"
    if template_requirements.exists():
        copy_file_with_status(template_requirements, target_requirements)

    template_backend_dockerfile = template_backend_root / "Dockerfile"
    target_backend_dockerfile = backend_path / "Dockerfile"
    if template_backend_dockerfile.exists():
        copy_file_with_status(template_backend_dockerfile, target_backend_dockerfile)

    nuitka_entrypoint_src = template_backend_root / "nuitka_entrypoint.py"
    nuitka_entrypoint_dst = backend_path / "nuitka_entrypoint.py"
    if nuitka_entrypoint_src.exists():
        copy_file_with_status(nuitka_entrypoint_src, nuitka_entrypoint_dst)

    pagination_schema_src = template_backend_root / "app" / "schemas" / "pagination.py"
    pagination_schema_dst = backend_path / "app" / "schemas" / "pagination.py"
    if pagination_schema_src.exists():
        copy_file_with_status(pagination_schema_src, pagination_schema_dst)

    token_schema_src = template_backend_root / "app" / "schemas" / "token.py"
    token_schema_dst = backend_path / "app" / "schemas" / "token.py"
    if token_schema_src.exists():
        copy_file_with_status(token_schema_src, token_schema_dst)
