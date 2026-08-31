"""Typed declarations for developer-owned frontend features.

Frontend feature source lives below ``app/frontend/features/<name>``.  A
feature exports one :class:`FrontendFeature` from its adjacent ``feature.py``;
``site sync`` validates the declaration, mirrors the TypeScript source, and
generates the integration registry consumed by the frontend shell.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .config import Role


class _FrontendDeclaration(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DashboardWidget(_FrontendDeclaration):
    """One custom card rendered in the generated Dashboard grid."""

    id: str
    component: str
    title: dict[Literal["zh", "en"], str]
    span: int | dict[Literal["sm", "md", "lg", "xl", "2xl"], int] = 12
    order: int = 100
    access: list[Role] = Field(
        default_factory=lambda: ["user", "admin", "developer"]
    )
    frame: bool = True


class FrontendMenu(_FrontendDeclaration):
    """Sidebar metadata for an application route."""

    title: dict[Literal["zh", "en"], str]
    icon: str = "PanelsTopLeft"
    visible: list[Role] | None = None


class FrontendRoute(_FrontendDeclaration):
    """One route contributed by a frontend feature."""

    id: str
    path: str
    component: str
    layout: Literal["app", "public"] = "app"
    access: list[Role] = Field(
        default_factory=lambda: ["user", "admin", "developer"]
    )
    menu: FrontendMenu | None = None


class FrontendOverride(_FrontendDeclaration):
    """Replace the component rendered by one stable generated route ID."""

    target: str
    component: str
    access: list[Role] | None = None


class FrontendFeature(_FrontendDeclaration):
    """A self-contained developer-owned frontend feature."""

    name: str
    routes: list[FrontendRoute] = Field(default_factory=list)
    overrides: list[FrontendOverride] = Field(default_factory=list)
    dashboard_widgets: list[DashboardWidget] = Field(default_factory=list)
    dependencies: dict[str, str] = Field(default_factory=dict)
    dev_dependencies: dict[str, str] = Field(default_factory=dict)
    locales: dict[Literal["zh", "en"], str] = Field(default_factory=dict)
