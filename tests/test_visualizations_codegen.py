"""Project-level visualization DSL, validation, and generation coverage."""

from datetime import datetime
from enum import Enum
import json
from pathlib import Path
from typing import Optional

import pytest
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict
from onesite.codegen.phases.relationships import phase_resolve_relationships
from onesite.codegen.router import update_api_router
from onesite.codegen.visualizations import compile_visualizations, load_visualizations
from onesite.visualization import (
    chart,
    count,
    dim,
    heatmap,
    line,
    metric,
    pie,
    radar,
    sankey,
    scatter,
    sunburst,
    tree,
    tree_leaf,
    treemap,
)


class VizLevel(str, Enum):
    LOW = "LOW"
    HIGH = "HIGH"

    __i18n__ = {
        "en": {"LOW": "Low", "HIGH": "High"},
        "zh": {"LOW": "低", "HIGH": "高"},
    }


class VizCategory(SQLModel, table=True):
    __tablename__ = "viz_category"
    __onesite__ = {"permissions": {"user": "r", "admin": "crud", "developer": "crud"}}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class VizOrder(SQLModel, table=True):
    __tablename__ = "viz_order"
    __onesite__ = {"permissions": {"user": "r", "admin": "crud", "developer": "crud"}}

    id: Optional[int] = Field(default=None, primary_key=True)
    amount: float
    channel: str
    status: str
    level: VizLevel = VizLevel.LOW
    created_at: datetime
    category_id: int = Field(foreign_key="viz_category.id")


class VizGroup(SQLModel, table=True):
    __tablename__ = "viz_group"
    __onesite__ = {"permissions": {"user": "r", "admin": "crud", "developer": "crud"}}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    parent_id: Optional[int] = Field(default=None, foreign_key="viz_group.id")


class VizDevice(SQLModel, table=True):
    __tablename__ = "viz_device"
    __onesite__ = {"permissions": {"user": "r", "admin": "crud", "developer": "crud"}}

    id: str = Field(primary_key=True)
    name: str
    group_id: int = Field(foreign_key="viz_group.id")


def _models():
    models = []
    for model_class, module in (
        (VizCategory, "viz_category"),
        (VizOrder, "viz_order"),
        (VizGroup, "viz_group"),
        (VizDevice, "viz_device"),
    ):
        result = get_model_fields(model_class, module)
        models.append(_build_model_dict(model_class.__name__, module, module, result, table_name=model_class.__tablename__))
    phase_resolve_relationships(models)
    return models


def _templates():
    root = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    return Environment(loader=FileSystemLoader(root))


def test_visualization_preset_constants_match_compiler_registry():
    public_presets = {
        line.basic,
        line.smooth,
        line.area,
        line.stacked,
        line.stacked_area,
        line.stacked_area_gradient,
        scatter.basic,
        scatter.category,
        pie.donut,
        pie.rounded_donut,
        pie.half_donut,
        heatmap.cartesian,
        radar.basic,
        tree.basic,
        treemap.basic,
        sunburst.basic,
        sankey.basic,
    }

    from onesite.codegen.visualizations import PRESETS

    assert public_presets == set(PRESETS)
    assert line.stacked_area_gradient == "line.stacked_area_gradient"


def test_visualization_dsl_compiles_multi_series_and_fk_paths():
    declarations = [
        chart(
            "sales_by_channel",
            title="Sales by channel",
            preset=line.stacked_area_gradient,
            model="VizOrder",
            x=dim("created_at", bucket="day"),
            series=dim("category.name"),
            y=metric("amount", aggregate="sum", label="Sales"),
            where={"status": "paid"},
            filters=[{"key": "channel", "field": "channel", "type": "select"}],
            visible=["admin", "developer"],
        ).to_dict(),
        chart(
            "order_totals",
            title="Order totals",
            preset="line.stacked_area",
            model="VizOrder",
            x=dim("created_at", bucket="day"),
            y=[
                metric("amount", aggregate="sum", label="Sales"),
                count(label="Orders"),
            ],
        ).to_dict(),
    ]

    compiled = compile_visualizations(declarations, _models())

    assert [item["key"] for item in compiled] == ["order_totals", "sales_by_channel"]
    sales = compiled[1]
    assert sales["contract"] == "xy_series"
    assert sales["inputs"]["series"]["field"] == "name"
    assert sales["inputs"]["series"]["joins"][0]["left_field"] == "category_id"
    assert sales["permitted_roles"] == ["admin", "developer"]
    assert compiled[0]["inputs"]["y"][1]["aggregate"] == "count"


def test_visualization_relative_time_where_compiles_and_validates_date_fields():
    compiled = compile_visualizations([
        chart(
            "today_orders", title="Today orders", preset=pie.donut, model="VizOrder",
            category=dim("status"), value=count(),
            where={"created_at": {"period": "today"}},
        ).to_dict()
    ], _models())

    assert compiled[0]["where"][0]["value"] == {"period": "today"}

    with pytest.raises(ValueError, match="one of: .*today"):
        compile_visualizations([
            chart(
                "bad_period", title="Bad period", preset=pie.donut, model="VizOrder",
                category=dim("status"), value=count(),
                where={"created_at": {"period": "tomorrow"}},
            ).to_dict()
        ], _models())

    with pytest.raises(ValueError, match="must be a date or datetime field"):
        compile_visualizations([
            chart(
                "wrong_type", title="Wrong type", preset=pie.donut, model="VizOrder",
                category=dim("status"), value=count(),
                where={"status": {"period": "today"}},
            ).to_dict()
        ], _models())


def test_visualization_validation_reports_contract_and_type_errors():
    with pytest.raises(ValueError, match="requires input.*y"):
        compile_visualizations([
            chart(
                "missing_y", title="Missing", preset="line.basic", model="VizOrder",
                x=dim("created_at"),
            ).to_dict()
        ], _models())

    with pytest.raises(ValueError, match="must produce numeric values"):
        compile_visualizations([
            chart(
                "bad_value", title="Bad", preset="pie.donut", model="VizOrder",
                category=dim("channel"), value=metric("status", aggregate="max"),
            ).to_dict()
        ], _models())


def test_tree_visualization_compiles_a_direct_fk_leaf_model():
    compiled = compile_visualizations([
        chart(
            "devices_by_group",
            title="Devices by group",
            preset=tree.basic,
            model="VizGroup",
            id=dim("id"), parent=dim("parent_id"), name=dim("name"),
            leaf=tree_leaf(
                model="VizDevice",
                id=dim("id"), parent=dim("group_id"), name=dim("name"),
            ),
        ).to_dict(),
    ], _models())

    leaf = compiled[0]["leaf"]
    assert leaf["model"]["name"] == "VizDevice"
    assert leaf["inputs"]["parent"]["field"] == "group_id"


def test_tree_leaf_requires_a_direct_fk_to_its_hierarchy_model():
    with pytest.raises(ValueError, match="must be a direct foreign key"):
        compile_visualizations([
            chart(
                "invalid_tree_leaf",
                title="Invalid tree leaf",
                preset=tree.basic,
                model="VizGroup",
                id=dim("id"), parent=dim("parent_id"), name=dim("name"),
                leaf=tree_leaf(
                    model="VizDevice",
                    id=dim("id"), parent=dim("id"), name=dim("name"),
                ),
            ).to_dict(),
        ], _models())


def test_tree_leaf_query_filters_before_limit_and_has_its_own_budget():
    compiled = compile_visualizations([
        chart(
            "devices_by_group",
            title="Devices by group",
            preset=tree.basic,
            model="VizGroup",
            id=dim("id"), parent=dim("parent_id"), name=dim("name"),
            leaf=tree_leaf(
                model="VizDevice",
                id=dim("id"), parent=dim("group_id"), name=dim("name"),
            ),
        ).to_dict(),
    ], _models())
    runtime = _templates().get_template("visualization_runtime.py.j2").render(
        visualizations=compiled,
        visualizations_json=json.dumps(compiled),
    )

    assert 'parent_binding = leaf["inputs"]["parent"]' in runtime
    assert "statement = statement.where(" in runtime
    assert "parent_column.in_(" in runtime
    assert "limit=limit," in runtime
    assert "limit=max(limit - len(rows), 0)" not in runtime


def test_enum_filter_exposes_frontend_i18n_key():
    compiled = compile_visualizations([
        chart(
            "orders_by_level", title="Orders by level", preset="pie.donut",
            model="VizOrder", category=dim("level"), value=count(),
            filters=[{"key": "level", "field": "level", "type": "select"}],
        ).to_dict()
    ], _models())

    assert compiled[0]["filters"][0]["option_i18n_key"] == (
        "models.viz_order.enums.level"
    )


def test_visualizations_file_loader_accepts_public_dsl(tmp_path):
    (tmp_path / "visualizations.py").write_text(
        "from onesite.visualization import chart, count, dim, pie\n"
        "visualizations = [chart('orders', title='Orders', preset=pie.donut, "
        "model='VizOrder', category=dim('status'), value=count())]\n",
        encoding="utf-8",
    )

    declarations = load_visualizations(tmp_path)

    assert declarations[0]["key"] == "orders"
    assert declarations[0]["inputs"]["value"]["aggregate"] == "count"


def test_generated_visualization_backend_and_frontend_templates_compile(tmp_path):
    compiled = compile_visualizations([
        chart(
            "orders", title="Orders", preset="pie.rounded_donut", model="VizOrder",
            category=dim("status"), value=count(),
            filters=[{"key": "level", "field": "level", "type": "select"}],
        ).to_dict()
    ], _models())
    env = _templates()
    context = {"visualizations": compiled, "visualizations_json": json.dumps(compiled)}
    runtime = env.get_template("visualization_runtime.py.j2").render(**context)
    api = env.get_template("visualizations_api.py.j2").render(**context)
    service = env.get_template("frontend_visualization_service.ts.j2").render(**context)
    chart_component = env.get_template("frontend_visualization_chart.tsx.j2").render(**context)

    compile(runtime, "generated_visualizations_runtime.py", "exec")
    compile(api, "generated_visualizations_api.py", "exec")
    runtime_namespace = {}
    exec(runtime, runtime_namespace)
    assert runtime_namespace["_serialize"](VizLevel.HIGH) == "HIGH"
    public_spec = runtime_namespace["_public_spec"](compiled[0])
    assert public_spec["filters"][0]["option_i18n_key"] == (
        "models.viz_order.enums.level"
    )
    assert "query_visualization" in runtime
    assert "if isinstance(value, Enum):" in runtime
    assert 'prefix="/visualizations"' not in api
    assert "queryVisualization" in service
    assert "buildVisualizationOption" in chart_component
    assert "PieChart" in chart_component
    assert "SankeyChart" not in chart_component

    api_path = tmp_path / "api.py"
    update_api_router([], api_path, visualizations_enabled=True)
    generated_router = api_path.read_text(encoding="utf-8")
    assert "from app.api.endpoints import visualizations" in generated_router
    assert 'prefix="/visualizations"' in generated_router


def test_dashboard_includes_new_visualization_runtime():
    compiled = compile_visualizations([
        chart(
            "orders", title="Orders", preset="pie.donut", model="VizOrder",
            category=dim("status"), value=count(),
        ).to_dict()
    ], _models())
    dashboard = _templates().get_template("dashboard_page.tsx.j2").render(
        models=[], dashboard_models=[], scheduled_tasks=[], site_logger=False,
        show_dashboard_announcement=False, tools=[], dashboard_metric_icons=[],
        visualizations=compiled,
    )

    assert "getVisualizations" in dashboard
    assert "queryVisualization" in dashboard
    assert "<VisualizationChart" in dashboard
    assert "filter.option_i18n_key" in dashboard
    assert "from '../components/ui/select'" in dashboard
    assert '<SelectTrigger className="h-9 w-44 max-w-full text-xs">' in dashboard
    assert "value === '__all__' ? '' : value" in dashboard
    assert "<SearchableSelect" in dashboard
    assert "<select " not in dashboard


def test_dashboard_deduplicates_builtin_metric_icons():
    dashboard = _templates().get_template("dashboard_page.tsx.j2").render(
        models=[], dashboard_models=[], scheduled_tasks=[], site_logger=False,
        show_dashboard_announcement=False, tools=[],
        dashboard_metric_icons=["RefreshCw"], visualizations=[],
    )

    import_line = dashboard.splitlines()[2]
    assert import_line.count("RefreshCw") == 1
