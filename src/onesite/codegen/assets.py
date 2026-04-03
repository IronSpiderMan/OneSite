import shutil
from pathlib import Path
from typing import Any, Dict, List

from rich.console import Console

from .render import generate_file

console = Console()

def _ensure_init_py(dir_path: Path) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    init_file = dir_path / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")


def sync_frontend_assets(cwd: Path, site_config: Dict[str, Any]):
    template_root = Path(__file__).resolve().parent.parent / "templates" / "frontend"
    target_frontend_root = cwd / "frontend"

    template_components_dir = template_root / "src" / "components" / "ui"
    target_components_dir = target_frontend_root / "src" / "components" / "ui"
    if template_components_dir.exists():
        target_components_dir.mkdir(parents=True, exist_ok=True)
        for item in template_components_dir.glob("*"):
            if item.is_file():
                shutil.copy2(item, target_components_dir / item.name)
        console.print(f"Synced UI components to {target_components_dir}")

    template_utils_dir = template_root / "src" / "utils"
    target_utils_dir = target_frontend_root / "src" / "utils"
    if template_utils_dir.exists():
        target_utils_dir.mkdir(parents=True, exist_ok=True)
        for item in template_utils_dir.glob("*"):
            if item.is_file():
                shutil.copy2(item, target_utils_dir / item.name)
        console.print(f"Synced Utils to {target_utils_dir}")

    template_lib_dir = template_root / "src" / "lib"
    target_lib_dir = target_frontend_root / "src" / "lib"
    if template_lib_dir.exists():
        target_lib_dir.mkdir(parents=True, exist_ok=True)
        for item in template_lib_dir.glob("*"):
            if item.is_file():
                shutil.copy2(item, target_lib_dir / item.name)
        console.print(f"Synced lib to {target_lib_dir}")

    config_files: List[str] = [
        "package.json",
        "tailwind.config.js",
        "postcss.config.js",
        "tsconfig.json",
        "tsconfig.node.json",
        "vite.config.ts",
        "index.html",
        "src/main.tsx",
        "src/App.tsx",
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
        "src/components/ui/file-upload.tsx",
        "src/components/ui/file-preview.tsx",
        "src/components/Layout.tsx",
        "src/utils/request.ts",
        "src/pages/Login.tsx",
        "src/pages/ErrorPage.tsx",
        "src/pages/Profile.tsx",
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

        src = template_root / config_file
        dst = target_frontend_root / config_file
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            console.print(f"Synced config file: {config_file}")

    generate_file("frontend_nginx.conf.j2", {"config": site_config}, target_frontend_root / "nginx.conf")

    template_frontend_dockerfile = template_root / "Dockerfile"
    target_frontend_dockerfile = target_frontend_root / "Dockerfile"
    if template_frontend_dockerfile.exists():
        shutil.copy2(template_frontend_dockerfile, target_frontend_dockerfile)
        console.print("Synced frontend Dockerfile")


def sync_backend_assets(cwd: Path, backend_path: Path, site_config: Dict[str, Any]):
    template_backend_root = Path(__file__).resolve().parent.parent / "templates" / "backend"

    _ensure_init_py(backend_path / "app")
    _ensure_init_py(backend_path / "app" / "api")
    _ensure_init_py(backend_path / "app" / "api" / "endpoints")
    _ensure_init_py(backend_path / "app" / "core")
    _ensure_init_py(backend_path / "app" / "cruds")
    _ensure_init_py(backend_path / "app" / "schemas")
    _ensure_init_py(backend_path / "app" / "services")

    template_endpoints_dir = template_backend_root / "app" / "api" / "endpoints"
    target_endpoints_dir = backend_path / "app" / "api" / "endpoints"
    if template_endpoints_dir.exists():
        target_endpoints_dir.mkdir(parents=True, exist_ok=True)
        generate_file("backend_api_upload.py.j2", {"config": site_config}, target_endpoints_dir / "upload.py")
        login_py = template_endpoints_dir / "login.py"
        if login_py.exists():
            shutil.copy2(login_py, target_endpoints_dir / "login.py")
            console.print("Synced backend endpoint: login.py")

    generate_file("backend_config.py.j2", {"config": site_config}, backend_path / "app" / "core" / "config.py")
    generate_file("backend_main.py.j2", {"config": site_config}, backend_path / "app" / "main.py")

    for name in ["security.py", "db.py", "deps.py", "tablenames.py"]:
        src = template_backend_root / "app" / "core" / name
        dst = backend_path / "app" / "core" / name
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            console.print(f"Synced backend {name}")

    initial_data_src = template_backend_root / "app" / "initial_data.py"
    initial_data_dst = backend_path / "app" / "initial_data.py"
    if initial_data_src.exists():
        initial_data_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(initial_data_src, initial_data_dst)
        console.print("Synced backend initial_data.py")

    template_requirements = template_backend_root / "requirements.txt"
    target_requirements = backend_path / "requirements.txt"
    if template_requirements.exists():
        shutil.copy2(template_requirements, target_requirements)
        console.print("Synced requirements.txt")

    template_backend_dockerfile = template_backend_root / "Dockerfile"
    target_backend_dockerfile = backend_path / "Dockerfile"
    if template_backend_dockerfile.exists():
        shutil.copy2(template_backend_dockerfile, target_backend_dockerfile)
        console.print("Synced backend Dockerfile")

    pagination_schema_src = template_backend_root / "app" / "schemas" / "pagination.py"
    pagination_schema_dst = backend_path / "app" / "schemas" / "pagination.py"
    if pagination_schema_src.exists():
        pagination_schema_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pagination_schema_src, pagination_schema_dst)
        console.print(f"Synced pagination schema to {pagination_schema_dst}")

    token_schema_src = template_backend_root / "app" / "schemas" / "token.py"
    token_schema_dst = backend_path / "app" / "schemas" / "token.py"
    if token_schema_src.exists():
        token_schema_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(token_schema_src, token_schema_dst)
        console.print(f"Synced token schema to {token_schema_dst}")
