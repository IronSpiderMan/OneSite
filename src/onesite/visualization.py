"""Public declarative API for project-level visualization definitions.

Projects import the helpers in this module from their root ``visualizations.py``
file.  The objects are deliberately small data containers: query planning and
model validation happen later in :mod:`onesite.codegen.visualizations`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field as dataclass_field
from typing import Any, Final, Mapping, Sequence


class _LinePresets:
    """Line and area chart presets."""

    __slots__ = ()

    basic: Final = "line.basic"
    smooth: Final = "line.smooth"
    area: Final = "line.area"
    stacked: Final = "line.stacked"
    stacked_area: Final = "line.stacked_area"
    stacked_area_gradient: Final = "line.stacked_area_gradient"


class _ScatterPresets:
    """Scatter chart presets."""

    __slots__ = ()

    basic: Final = "scatter.basic"
    category: Final = "scatter.category"


class _PiePresets:
    """Pie and donut chart presets."""

    __slots__ = ()

    donut: Final = "pie.donut"
    rounded_donut: Final = "pie.rounded_donut"
    half_donut: Final = "pie.half_donut"


class _HeatmapPresets:
    """Heatmap chart presets."""

    __slots__ = ()

    cartesian: Final = "heatmap.cartesian"


class _RadarPresets:
    """Radar chart presets."""

    __slots__ = ()

    basic: Final = "radar.basic"


class _TreePresets:
    """Tree chart presets."""

    __slots__ = ()

    basic: Final = "tree.basic"


class _TreemapPresets:
    """Treemap chart presets."""

    __slots__ = ()

    basic: Final = "treemap.basic"


class _SunburstPresets:
    """Sunburst chart presets."""

    __slots__ = ()

    basic: Final = "sunburst.basic"


class _SankeyPresets:
    """Sankey chart presets."""

    __slots__ = ()

    basic: Final = "sankey.basic"


# Public preset namespaces keep declarations typo-safe and discoverable through
# editor completion while remaining plain strings at the chart() boundary.
line: Final = _LinePresets()
scatter: Final = _ScatterPresets()
pie: Final = _PiePresets()
heatmap: Final = _HeatmapPresets()
radar: Final = _RadarPresets()
tree: Final = _TreePresets()
treemap: Final = _TreemapPresets()
sunburst: Final = _SunburstPresets()
sankey: Final = _SankeyPresets()


@dataclass(frozen=True)
class DataBinding:
    """Map one semantic chart input to a model field or aggregate."""

    kind: str
    field: str | None = None
    aggregate: str | None = None
    label: str | None = None
    bucket: str | None = None
    extract: str | None = None
    unit: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in asdict(self).items()
            if value is not None
        }


@dataclass(frozen=True)
class HierarchyLeaf:
    """A non-recursive model rendered as leaves below a hierarchy model.

    ``parent`` must bind to a direct foreign-key field on ``model`` that
    targets the chart's hierarchy model.  The compiler validates that
    relationship before generating the visualization query.
    """

    model: str | type
    id: DataBinding
    parent: DataBinding
    name: DataBinding
    value: DataBinding | None = None

    def to_dict(self) -> dict[str, Any]:
        model_name = self.model if isinstance(self.model, str) else self.model.__name__
        inputs = {
            "id": self.id.to_dict(),
            "parent": self.parent.to_dict(),
            "name": self.name.to_dict(),
        }
        if self.value is not None:
            inputs["value"] = self.value.to_dict()
        return {"model": model_name, "inputs": inputs}


@dataclass(frozen=True)
class Visualization:
    """A chart declaration returned by :func:`chart`."""

    key: str
    title: str
    preset: str
    model: str | type
    inputs: Mapping[str, DataBinding | Sequence[DataBinding]]
    where: Mapping[str, Any] = dataclass_field(default_factory=dict)
    filters: Sequence[Mapping[str, Any]] = dataclass_field(default_factory=tuple)
    order_by: Sequence[str] = dataclass_field(default_factory=tuple)
    limit: int = 1000
    visible: Sequence[str] | None = None
    placement: Mapping[str, Any] = dataclass_field(default_factory=dict)
    options: Mapping[str, Any] = dataclass_field(default_factory=dict)
    leaf: HierarchyLeaf | None = None

    def to_dict(self) -> dict[str, Any]:
        model_name = self.model if isinstance(self.model, str) else self.model.__name__
        normalized_inputs: dict[str, Any] = {}
        for name, binding in self.inputs.items():
            if isinstance(binding, DataBinding):
                normalized_inputs[name] = binding.to_dict()
            else:
                normalized_inputs[name] = [item.to_dict() for item in binding]
        return {
            "key": self.key,
            "title": self.title,
            "preset": self.preset,
            "model": model_name,
            "inputs": normalized_inputs,
            "where": dict(self.where),
            "filters": [dict(item) for item in self.filters],
            "order_by": list(self.order_by),
            "limit": self.limit,
            "visible": list(self.visible) if self.visible is not None else None,
            "placement": dict(self.placement),
            "options": dict(self.options),
            "leaf": self.leaf.to_dict() if self.leaf is not None else None,
        }


@dataclass(frozen=True)
class DashboardMetric:
    """A project-level Dashboard KPI declaration.

    Unlike charts, metrics are evaluated by the generated endpoint for their
    source model.  Keeping the declaration here still lets projects put all
    Dashboard presentation configuration in ``visualizations.py``.
    """

    key: str
    model: str | type
    title: str
    aggregation: str = "count"
    field: str | None = None
    where: Mapping[str, Any] = dataclass_field(default_factory=dict)
    # Legacy aliases. Prefer where={"created_at": {"period": "today"}}.
    time_field: str | None = None
    period: str | None = None
    compare: str | None = None
    format: Mapping[str, Any] | None = None
    visible: Sequence[str] | None = None
    icon: str | None = None
    color: str | None = None
    order: int | float | None = None
    link: str | None = None
    items: Sequence[Mapping[str, Any]] | None = None
    separator: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a plain declaration consumed by the code generator."""

        model_name = self.model if isinstance(self.model, str) else self.model.__name__
        result = {
            "key": self.key,
            "model": model_name,
            "title": self.title,
            "aggregation": self.aggregation,
            "where": dict(self.where),
        }
        for name, value in (
            ("field", self.field),
            ("time_field", self.time_field),
            ("period", self.period),
            ("compare", self.compare),
            ("format", dict(self.format) if self.format is not None else None),
            ("visible", list(self.visible) if self.visible is not None else None),
            ("icon", self.icon),
            ("color", self.color),
            ("order", self.order),
            ("link", self.link),
            ("items", [dict(item) for item in self.items] if self.items is not None else None),
            ("separator", self.separator),
        ):
            if value is not None:
                result[name] = value
        return result


def dim(
    field: str,
    *,
    label: str | None = None,
    bucket: str | None = None,
    extract: str | None = None,
    unit: str | None = None,
) -> DataBinding:
    """Declare a non-aggregated dimension binding."""

    return DataBinding(
        kind="dimension",
        field=field,
        label=label,
        bucket=bucket,
        extract=extract,
        unit=unit,
    )


def metric(
    field: str,
    *,
    aggregate: str,
    label: str | None = None,
    unit: str | None = None,
) -> DataBinding:
    """Declare an aggregated numeric measure binding."""

    return DataBinding(
        kind="metric",
        field=field,
        aggregate=aggregate,
        label=label,
        unit=unit,
    )


def count(
    field: str | None = None,
    *,
    distinct: bool = False,
    label: str | None = None,
) -> DataBinding:
    """Declare a row count or distinct field count measure."""

    return DataBinding(
        kind="metric",
        field=field,
        aggregate="distinct_count" if distinct else "count",
        label=label or "Count",
    )


def tree_leaf(
    *,
    model: str | type,
    id: DataBinding,
    parent: DataBinding,
    name: DataBinding,
    value: DataBinding | None = None,
) -> HierarchyLeaf:
    """Attach one model's records as leaves of a hierarchy visualization.

    Use this with ``tree.basic`` when records from a second model belong below
    nodes from the chart model.  ``parent`` must be that second model's direct
    foreign key to the chart model.
    """

    return HierarchyLeaf(
        model=model,
        id=id,
        parent=parent,
        name=name,
        value=value,
    )


def dashboard_metric(
    key: str,
    *,
    model: str | type,
    title: str,
    aggregation: str = "count",
    field: str | None = None,
    where: Mapping[str, Any] | None = None,
    time_field: str | None = None,
    period: str | None = None,
    compare: str | None = None,
    format: Mapping[str, Any] | None = None,
    visible: Sequence[str] | None = None,
    icon: str | None = None,
    color: str | None = None,
    order: int | float | None = None,
    link: str | None = None,
    items: Sequence[Mapping[str, Any]] | None = None,
    separator: str | None = None,
) -> DashboardMetric:
    """Declare a Dashboard KPI in a project's ``visualizations.py`` file.

    Pass two or more calculation declarations through ``items`` to render a
    combined KPI in one Dashboard card. ``separator`` is placed between the
    values (for example ``" / "`` or ``" − "``); it defaults to ``" / "``.
    Each item accepts the usual calculation fields: ``aggregation``, ``field``,
    ``where`` and ``format``.
    """

    return DashboardMetric(
        key=key,
        model=model,
        title=title,
        aggregation=aggregation,
        field=field,
        where=where or {},
        time_field=time_field,
        period=period,
        compare=compare,
        format=format,
        visible=visible,
        icon=icon,
        color=color,
        order=order,
        link=link,
        items=items,
        separator=separator,
    )


def chart(
    key: str,
    *,
    title: str,
    preset: str,
    model: str | type,
    where: Mapping[str, Any] | None = None,
    filters: Sequence[Mapping[str, Any]] | None = None,
    order_by: Sequence[str] | None = None,
    limit: int = 1000,
    visible: Sequence[str] | None = None,
    placement: Mapping[str, Any] | None = None,
    options: Mapping[str, Any] | None = None,
    leaf: HierarchyLeaf | None = None,
    **inputs: DataBinding | Sequence[DataBinding],
) -> Visualization:
    """Create a project-level visualization declaration.

    Semantic inputs such as ``x``, ``y``, ``series`` and ``value`` are passed
    as keyword arguments.  Their required shape is determined by ``preset``.
    """

    return Visualization(
        key=key,
        title=title,
        preset=preset,
        model=model,
        inputs=inputs,
        where=where or {},
        filters=filters or (),
        order_by=order_by or (),
        limit=limit,
        visible=visible,
        placement=placement or {},
        options=options or {},
        leaf=leaf,
    )


__all__ = [
    "DashboardMetric",
    "DataBinding",
    "HierarchyLeaf",
    "Visualization",
    "chart",
    "count",
    "dashboard_metric",
    "dim",
    "heatmap",
    "line",
    "metric",
    "pie",
    "radar",
    "sankey",
    "scatter",
    "sunburst",
    "tree",
    "tree_leaf",
    "treemap",
]
