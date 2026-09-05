"""Code generation pipeline — orchestrates all codegen in discrete phases.

Each phase has its own module in :mod:`~onesite.codegen.phases`.
This module simply imports and calls them in order.
"""

import os
from pathlib import Path

from rich.console import Console

from .phases import config as phase_config
from .phases import finalize_standalone as phase_finalize_standalone
from .phases import generate as phase_generate
from .phases import introspect_models as phase_introspect
from .phases import model_tables as phase_model_tables
from .phases import plugin_models as phase_plugin_models
from .phases import relationships as phase_relationships
from .phases import sync_models as phase_sync_models
from .phases import theme_assets as phase_theme_assets
from .visualizations import (
    apply_dashboard_metrics,
    load_and_compile_dashboard_metrics,
    load_and_compile_visualizations,
)
from .frontend_features import load_frontend_features

console = Console()


def generate_code() -> None:
    from .transaction import staged_generation

    with staged_generation(Path.cwd().resolve()):
        _generate_staged_code()


def _generate_staged_code() -> None:
    """Load configuration, introspect models, and generate the full project.

    This is the public entry point called by ``site sync``.
    """
    cwd = Path(os.getcwd())

    # Phase 1 — Load typed configuration, then scaffold and compile the
    # SiteConfig-owned custom feature declarations.
    site_config, backend_path = phase_config.phase_load_config(cwd)
    frontend_features = load_frontend_features(
        cwd, site_config.get("custom_features", [])
    )
    site_config["_frontend_features"] = frontend_features

    # Phase 2 — Generate model tables (into models/, before sync so they are picked up)
    phase_model_tables.phase_generate_timeseries_artifacts(cwd, backend_path)

    # Phase 2.5 — Sync model files (copies generated + user models to backend)
    phase_sync_models.phase_sync_models(cwd, backend_path)

    # Phase 2.75 — Add generated plugin models after stale mirror files have
    # been removed, while still allowing project-owned models to override them.
    phase_plugin_models.phase_generate_plugin_models(
        site_config,
        cwd,
        backend_path,
    )

    # Phase 3 — Introspect
    models = phase_introspect.phase_introspect(backend_path)
    if not models:
        return

    # Phase 4 — Relationships
    phase_relationships.phase_resolve_relationships(models)

    # Project-level charts and KPIs are compiled only after relationships have
    # resolved FK and reverse-FK paths.  Keep charts in the transient
    # generation context; KPI metadata is attached to its source model.
    site_config["_visualizations"] = load_and_compile_visualizations(cwd, models)
    public_dashboard = site_config["public_dashboard"]
    public_keys = set(public_dashboard["visualizations"]) if public_dashboard["enabled"] else set()
    compiled_by_key = {item["key"]: item for item in site_config["_visualizations"]}
    unknown_public_keys = sorted(public_keys - set(compiled_by_key))
    if unknown_public_keys:
        available_keys = ", ".join(sorted(compiled_by_key)) or "(none declared in visualizations.py)"
        raise ValueError(
            "public_dashboard references unknown visualizations: "
            + ", ".join(unknown_public_keys)
            + ". Available visualization keys: "
            + available_keys
        )
    owner_scoped_keys = sorted(
        key for key in public_keys
        if compiled_by_key[key]["model"].get("owner_field")
        or (compiled_by_key[key].get("leaf") or {}).get("model", {}).get("owner_field")
    )
    if owner_scoped_keys:
        raise ValueError(
            "public_dashboard cannot expose owner-scoped visualizations: "
            + ", ".join(owner_scoped_keys)
        )
    site_config["_public_dashboard"] = {
        **public_dashboard,
        "visualizations": [item for item in site_config["_visualizations"] if item["key"] in public_keys],
    }
    apply_dashboard_metrics(
        models,
        load_and_compile_dashboard_metrics(cwd, models),
    )

    # Phase 5 — Theme & assets (before codegen so generated files aren't overwritten)
    phase_theme_assets.phase_theme_and_assets(site_config, cwd, backend_path)

    # Phase 6 — Per-model code
    api_models = phase_generate.phase_generate_per_model(
        models, site_config, cwd, backend_path
    )

    # Phase 7 — Aggregated code
    phase_generate.phase_generate_aggregated(
        models, api_models, site_config, cwd, backend_path
    )

    # Phase 8 — The generator metadata has served its purpose.  Remove it and
    # its imports so the generated application can run without OneSite.
    phase_finalize_standalone.phase_finalize_standalone(backend_path)

    from .migrations import generate_migrations
    generate_migrations(cwd, backend_path)
