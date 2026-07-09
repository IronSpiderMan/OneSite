"""Phase 5 — Theme generation and static asset sync.

Must run *before* per-model code generation (Phase 6) so that generated
files such as Settings.tsx are not overwritten by the asset sync.
"""

from pathlib import Path

from ..assets import sync_backend_assets, sync_frontend_assets
from ..file_utils import copy_file_with_status
from ..render import generate_file
from ..theme import THEMES, resolve_theme
from .base import console


def _sync_models_assets(site_config: dict, cwd: Path) -> None:
    """Copy assets from models/assets/ to frontend/public/.

    Users can place static files (e.g. logo, images) in ``models/assets/``
    and reference them in site_config.json (e.g. ``"logo": "logo.png"``).
    During sync these files are copied into ``frontend/public/`` so they
    are served by Vite's dev server and the production build.
    """
    assets_src = cwd / "models" / "assets"
    public_dst = cwd / "frontend" / "public"

    if not assets_src.exists():
        return

    counts = {"created": 0, "updated": 0, "skipped": 0}
    for item in assets_src.iterdir():
        if item.is_file():
            status = copy_file_with_status(item, public_dst / item.name)
            counts[status] += 1

    total = counts["created"] + counts["updated"]
    if total:
        console.print(
            f"[green]Synced {total} asset(s) from models/assets/ to frontend/public/[/green]"
        )


def phase_theme_and_assets(site_config: dict, cwd: Path, backend_path: Path) -> None:
    """Generate theme CSS and sync frontend / backend static assets.

    Must run *before* per-model generation so that generated files like
    Settings.tsx are not overwritten by the asset sync.
    """
    theme_config, radius = resolve_theme(site_config)
    generate_file(
        "index.css.j2",
        {"theme": theme_config, "themes": THEMES, "radius": radius},
        cwd / "frontend" / "src" / "index.css",
    )
    sync_frontend_assets(cwd, site_config)
    sync_backend_assets(cwd, backend_path, site_config)
    _sync_models_assets(site_config, cwd)
