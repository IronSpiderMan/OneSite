"""Project-level OneSite visualizations.

Keep chart declarations here instead of adding presentation configuration to
SQLModel classes.  Uncomment and adapt the example after adding an Order model.
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
    # A hierarchy model can be extended with records from one leaf model.
    # The leaf's ``parent`` must be a direct FK to the hierarchy model.
    # chart(
    #     "grouped_devices",
    #     title="Devices by group",
    #     preset=tree.basic,
    #     model="DeviceGroup",
    #     id=dim("id"), parent=dim("parent_id"), name=dim("name"),
    #     leaf=tree_leaf(
    #         model="Device",
    #         id=dim("id"), parent=dim("device_group_id"), name=dim("name"),
    #     ),
    # ),
    # chart(
    #     "orders_by_status",
    #     title="Orders by status",
    #     preset=pie.rounded_donut,
    #     model="Order",
    #     category=dim("status"),
    #     value=count(),
    # ),
    # chart(
    #     "daily_sales",
    #     title="Daily sales",
    #     preset=line.smooth,
    #     model="Order",
    #     x=dim("created_at", bucket="day"),
    #     y=metric("amount", aggregate="sum"),
    # ),
]


# Dashboard KPIs are also project-level presentation configuration.  They are
# generated into the source model's existing dashboard-metrics endpoint.
dashboard_metrics = [
    # dashboard_metric(
    #     "today_order_count",
    #     model="Order",
    #     title="Today's orders",
    #     aggregation="count",
    #     where={"created_at": {"period": "today"}},
    #     icon="ShoppingCart",
    #     color="blue",
    #     order=1,
    # ),
]
