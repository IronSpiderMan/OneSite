"""Code generation pipeline — orchestrates all codegen in discrete phases.

Each phase has its own module in :mod:`~onesite.codegen.phases`.
This module simply imports and calls them in order.
"""

import os
from pathlib import Path

from rich.console import Console

from .phases import config as phase_config
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

console = Console()


def generate_code() -> None:
    """Load configuration, introspect models, and generate the full project.

    This is the public entry point called by ``site sync``.
    """
    cwd = Path(os.getcwd())

    # Phase 1 — Config. Validate it before creating or modifying generated
    # project files so malformed input cannot be replaced by defaults.
    site_config, backend_path = phase_config.phase_load_config(cwd)

    # Phase 2 — Generate model tables (into models/, before sync so they are picked up)
    phase_model_tables.phase_generate_model_tables(cwd, backend_path)

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
    legacy_dashboard_metrics = [
        model["name"] for model in models if model.get("dashboard_metrics")
    ]
    apply_dashboard_metrics(
        models,
        load_and_compile_dashboard_metrics(cwd, models),
    )
    legacy_visualizations = [model["name"] for model in models if model.get("visualize")]
    if legacy_visualizations:
        console.print(
            "[yellow]Model-level __onesite__.visualize is deprecated. "
            "Move these charts to visualizations.py: "
            + ", ".join(legacy_visualizations)
            + "[/yellow]"
        )
    if legacy_dashboard_metrics:
        console.print(
            "[yellow]Model-level __onesite__.dashboard_metrics is deprecated. "
            "Move these KPIs to visualizations.py: "
            + ", ".join(legacy_dashboard_metrics)
            + "[/yellow]"
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
