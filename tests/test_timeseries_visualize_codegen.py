"""Legacy model visualization support for TimescaleDB-backed models."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
TEMPLATES = ROOT / "src" / "onesite" / "templates" / "codegen"


def test_visualization_count_does_not_require_an_id_field():
    source = (TEMPLATES / "service.py.j2").read_text(encoding="utf-8")

    assert "agg_expr = func.count()" in source
    assert "select(label_col, func.count())" in source
    assert "func.count(model.id)" not in source


def test_timeseries_frontend_service_can_emit_legacy_visualization_client():
    source = (TEMPLATES / "frontend_service.ts.j2").read_text(encoding="utf-8")

    visualization = source.index("{% if model.visualize %}")
    timeseries = source.index("{% if model.is_timescaledb %}")
    assert visualization < timeseries


def test_explicit_timeseries_visualizations_are_passed_to_dashboard():
    source = (
        ROOT / "src" / "onesite" / "codegen" / "phases" / "generate.py"
    ).read_text(encoding="utf-8")

    assert "visualize_models = [" in source
    assert 'bool((m.get("visualize") or {}).get("show"))' in source
    assert '"models": visualize_models' in source
