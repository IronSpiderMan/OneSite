"""Project-level OneSite visualizations for the data hub example.

Charts and KPIs live here instead of on the SQLModel classes, so presentation
stays decoupled from the data models.
"""

from onesite.visualization import (
    chart,
    count,
    dashboard_metric,
    dim,
    line,
    metric,
    pie,
    tree,
    tree_leaf,
)


visualizations = [
    # Regression/demo chart for hierarchy leaves.  AssetDocument records are
    # rendered as terminal nodes below their AssetFolder parent, even when the
    # folder query reaches the configured visualization limit.
    chart(
        "documents_by_folder",
        title="Documents by folder",
        preset=tree.basic,
        model="AssetFolder",
        id=dim("id"),
        parent=dim("parent_id"),
        name=dim("name"),
        leaf=tree_leaf(
            model="AssetDocument",
            id=dim("id"),
            parent=dim("folder_id"),
            name=dim("name", label="Document"),
        ),
    ),
    chart(
        "datasets_by_type",
        title="Datasets by type",
        preset=pie.rounded_donut,
        model="Dataset",
        category=dim("type"),
        value=count(),
    ),
    chart(
        "datasets_by_status",
        title="Datasets by status",
        preset=pie.donut,
        model="Dataset",
        category=dim("status"),
        value=count(),
    ),
    chart(
        "sync_tasks_by_frequency",
        title="Sync tasks by frequency",
        preset=pie.rounded_donut,
        model="SyncTask",
        category=dim("frequency"),
        value=count(),
    ),
    chart(
        "quality_rules_by_severity",
        title="Quality rules by severity",
        preset=pie.donut,
        model="DataQualityRule",
        category=dim("severity"),
        value=count(),
    ),
]


# Dashboard KPIs reuse each source model's generated endpoint, so the existing
# field validation and role-permission checks still apply.
dashboard_metrics = [
    dashboard_metric(
        "dataset_count",
        model="Dataset",
        title="Datasets",
        aggregation="count",
        icon="Table2",
        color="blue",
        order=1,
    ),
    dashboard_metric(
        "published_over_total",
        model="Dataset",
        title="Published / total datasets",
        items=[
            {"aggregation": "count", "where": {"status": "published"}},
            {"aggregation": "count"},
        ],
        separator=" / ",
        icon="CheckCircle2",
        color="purple",
        order=2,
    ),
    dashboard_metric(
        "source_count",
        model="DataSource",
        title="Data sources",
        aggregation="count",
        icon="Database",
        color="teal",
        order=3,
    ),
    dashboard_metric(
        "enabled_sync_tasks",
        model="SyncTask",
        title="Active sync tasks",
        aggregation="count",
        where={"is_enabled": True},
        icon="RefreshCw",
        color="green",
        order=4,
    ),
]
