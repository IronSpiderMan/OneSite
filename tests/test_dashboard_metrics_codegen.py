"""Dashboard KPI configuration and generated code coverage."""

from datetime import datetime
import json
from pathlib import Path
from typing import Optional

import pytest
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.i18n import generate_locale_files
from onesite.codegen.phases.introspect_models import _build_model_dict
from onesite.codegen.visualizations import (
    apply_dashboard_metrics,
    compile_dashboard_metrics,
    load_dashboard_metrics,
)
from onesite.visualization import dashboard_metric


class MetricOrder(SQLModel, table=True):
    __tablename__ = "test_metric_order"
    __onesite__ = {
        "permissions": {"user": "r", "admin": "crud", "developer": "crud"},
        "dashboard_metrics": [
            {
                "key": "paid_revenue_today",
                "title": "今日成交额",
                "field": "amount",
                "aggregation": "sum",
                "where": {
                    "status": "paid",
                    "created_at": {"period": "today"},
                },
                "compare": "previous_period",
                "format": {"type": "currency", "currency": "CNY", "decimals": 2},
                "visible": ["admin", "developer"],
                "icon": "Wallet",
                "color": "green",
            },
            {"key": "total_orders", "title": "订单总数", "aggregation": "count"},
        ],
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    amount: float
    status: str
    created_at: datetime


def _model():
    result = get_model_fields(MetricOrder, "metric_order")
    model = _build_model_dict("MetricOrder", "metric_order", "metric_order", result)
    model.update(
        min_role_for_read="USER",
        min_role_for_create="ADMIN",
        min_role_for_update="ADMIN",
        min_role_for_delete="ADMIN",
        m2m_fields=[],
        reverse_m2m=[],
        inline_relations=[],
        definition_binding_meta=None,
        reverse_definition_bindings=[],
        is_timescaledb=False,
        timescaledb_entity_model=None,
        timescaledb_entity_target_table=None,
    )
    return model


def _templates():
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    return Environment(loader=FileSystemLoader(template_dir))


def test_dashboard_metrics_are_normalized_and_intersect_model_permissions():
    metrics = _model()["dashboard_metrics"]

    assert [metric["key"] for metric in metrics] == ["paid_revenue_today", "total_orders"]
    assert metrics[0]["permitted_roles"] == ["admin", "developer"]
    assert metrics[0]["i18n_key"] == "dashboard.metrics.metric_order.paid_revenue_today"
    assert metrics[0]["where"]["created_at"] == {"period": "today"}
    assert "time_field" not in metrics[0]
    assert "period" not in metrics[0]
    assert metrics[1]["permitted_roles"] == ["user", "admin", "developer"]
    assert metrics[1]["format"] == {"type": "number"}


def test_legacy_metric_time_fields_normalize_to_a_relative_where_condition():
    model = _model()
    compiled = compile_dashboard_metrics([
        {
            "key": "legacy_today_orders",
            "model": "MetricOrder",
            "title": "Today orders",
            "aggregation": "count",
            "time_field": "created_at",
            "period": "today",
            "compare": "previous_period",
        },
    ], [model])

    metric = compiled["MetricOrder"][0]
    assert metric["where"] == {"created_at": {"period": "today"}}
    assert "time_field" not in metric
    assert "period" not in metric


def test_project_dashboard_metrics_compile_and_attach_to_source_model(tmp_path):
    (tmp_path / "visualizations.py").write_text(
        "from onesite.visualization import dashboard_metric\n"
        "dashboard_metrics = [dashboard_metric(\n"
        "    'connector_count', model='MetricOrder', title='Data sources',\n"
        "    aggregation='count', icon='Server', color='green', order=1,\n"
        ")]\n",
        encoding="utf-8",
    )
    model = _model()
    model["dashboard_metrics"] = []

    compiled = compile_dashboard_metrics(load_dashboard_metrics(tmp_path), [model])
    apply_dashboard_metrics([model], compiled)

    assert model["dashboard_metrics"] == [{
        "key": "connector_count",
        "title": "Data sources",
        "aggregation": "count",
        "where": {},
        "visible": ["user", "admin", "developer"],
        "permitted_roles": ["user", "admin", "developer"],
        "format": {"type": "number"},
        "icon": "Server",
        "color": "green",
        "order": 1,
        "i18n_key": "dashboard.metrics.metric_order.connector_count",
    }]


def test_project_dashboard_metric_rejects_legacy_key_collision():
    model = _model()
    compiled = compile_dashboard_metrics([
        dashboard_metric(
            "total_orders", model="MetricOrder", title="Orders", aggregation="count"
        ).to_dict()
    ], [model])

    with pytest.raises(ValueError, match="configured both"):
        apply_dashboard_metrics([model], compiled)


def test_combined_dashboard_metric_normalizes_multiple_calculations():
    model = _model()
    model["dashboard_metrics"] = []
    compiled = compile_dashboard_metrics([
        dashboard_metric(
            "paid_over_total", model="MetricOrder", title="Paid / total orders",
            icon="ReceiptText", color="purple", separator=" / ",
            items=[
                {"aggregation": "count", "where": {"status": "paid"}},
                {"aggregation": "count"},
                {"aggregation": "sum", "field": "amount", "format": {"type": "currency", "currency": "CNY"}},
            ],
        ).to_dict(),
    ], [model])

    metric = compiled["MetricOrder"][0]
    assert metric["separator"] == " / "
    assert [item["aggregation"] for item in metric["items"]] == ["count", "count", "sum"]
    assert metric["items"][0]["where"] == {"status": "paid"}
    assert metric["items"][2]["format"] == {"type": "currency", "currency": "CNY"}
    assert "aggregation" not in metric
    assert "format" not in metric


def test_combined_dashboard_metric_rejects_invalid_items():
    model = _model()
    with pytest.raises(ValueError, match="at least two KPI calculations"):
        compile_dashboard_metrics([
            dashboard_metric(
                "only_one", model="MetricOrder", title="Only one",
                items=[{"aggregation": "count"}],
            ).to_dict(),
        ], [model])

    with pytest.raises(ValueError, match=r"items\[1\].field is required"):
        compile_dashboard_metrics([
            dashboard_metric(
                "missing_field", model="MetricOrder", title="Missing field",
                items=[{"aggregation": "count"}, {"aggregation": "sum"}],
            ).to_dict(),
        ], [model])


def test_dashboard_metric_generated_backend_is_valid_python_and_role_filtered():
    model = _model()
    env = _templates()
    service = env.get_template("service.py.j2").render(model=model)
    api = env.get_template("api.py.j2").render(model=model)

    compile(service, "generated_metric_service.py", "exec")
    compile(api, "generated_metric_api.py", "exec")
    assert "async def get_dashboard_metrics" in service
    assert 'if role not in metric.get("permitted_roles", [])' in service
    assert "expression = func.count()" in service
    assert "select(expression).select_from(model)" in service
    assert 'func.count(func.distinct(value_col))' in service
    assert "_relative_time_filter" in service
    assert 'for calculation in metric["items"]' in service
    assert '@router.get("/dashboard-metrics")' in api
    assert api.index('@router.get("/dashboard-metrics")') < api.index('@router.get("/{id}"')


def test_dashboard_metric_generated_frontend_fetches_and_renders_cards():
    model = _model()
    env = _templates()
    service = env.get_template("frontend_service.ts.j2").render(model=model)
    dashboard = env.get_template("dashboard_page.tsx.j2").render(
        models=[model], scheduled_tasks=[], site_logger=False,
        show_dashboard_announcement=False, tools=[], dashboard_metric_icons=["Wallet"],
    )

    assert "getMetricOrderDashboardMetrics" in service
    assert "`${API_URL}/dashboard-metrics`" in service
    assert "separator?: string" in service
    assert "Promise.allSettled(metricRequests)" in dashboard
    assert "formatMetricValue(metric)" in dashboard
    assert "metric.values?.length" in dashboard
    assert "formatMetricNumber(value.value, value.format)" in dashboard
    assert "metric.previous_value !== null" in dashboard


def test_dashboard_metric_i18n_accepts_null_language_packs(tmp_path):
    model = _model()
    model["translations"] = {"en": None, "zh": None}

    generate_locale_files([model], tmp_path)

    en = json.loads((tmp_path / "en.json").read_text())
    zh = json.loads((tmp_path / "zh.json").read_text())
    assert en["dashboard"]["metrics"]["metric_order"]["paid_revenue_today"] == "今日成交额"
    assert zh["dashboard"]["metrics"]["metric_order"]["paid_revenue_today"] == "今日成交额"


def test_timeseries_dashboard_metrics_generate_backend_frontend_and_dashboard_usage():
    model = _model()
    model.update(
        is_timescaledb=True,
        timescaledb_entity_field="id",
        timescaledb_metric_field=None,
        timescaledb_entity_sql_type="INTEGER",
    )
    env = _templates()

    service = env.get_template("service.py.j2").render(model=model)
    frontend_service = env.get_template("frontend_service.ts.j2").render(model=model)
    dashboard = env.get_template("dashboard_page.tsx.j2").render(
        models=[], dashboard_models=[model], scheduled_tasks=[], site_logger=False,
        show_dashboard_announcement=False, tools=[], dashboard_metric_icons=["Wallet"],
    )

    compile(service, "generated_timeseries_metric_service.py", "exec")
    assert "async def get_dashboard_metrics" in service
    assert "getMetricOrderDashboardMetrics" in frontend_service
    assert "import { getMetricOrderDashboardMetrics }" in dashboard
    assert "metricRequests.push(getMetricOrderDashboardMetrics())" in dashboard


@pytest.mark.parametrize(
    ("metric", "message"),
    [
        ({"key": "bad-key", "title": "Bad"}, "valid identifier"),
        ({"key": "x", "title": "X", "aggregation": "sum"}, "field is required"),
        ({"key": "x", "title": "X", "period": "today"}, "time_field is required"),
        ({"key": "x", "title": "X", "where": {"missing": 1}}, "does not exist"),
    ],
)
def test_invalid_dashboard_metric_configuration_fails_during_introspection(metric, message):
    class InvalidMetricModel(SQLModel, table=True):
        __tablename__ = f"invalid_metric_{abs(hash(str(metric)))}"
        __onesite__ = {"dashboard_metrics": [metric]}
        id: Optional[int] = Field(default=None, primary_key=True)

    with pytest.raises(ValueError, match=message):
        get_model_fields(InvalidMetricModel, "invalid_metric")
