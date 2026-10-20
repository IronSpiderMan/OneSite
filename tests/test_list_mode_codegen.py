"""Regression coverage for configurable collection page layouts."""

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict
from onesite.config import ListMode, OneSiteConfig, normalize_onesite_config


class GridItem(SQLModel, table=True):
    __tablename__ = "test_grid_item"
    __onesite__ = {"list_mode": "grid"}

    id: int | None = Field(default=None, primary_key=True)
    name: str
    image: str | None = None
    enabled: bool = True


class DefaultListItem(SQLModel, table=True):
    __tablename__ = "test_default_list_item"

    id: int | None = Field(default=None, primary_key=True)
    name: str


class InvalidListModeItem(SQLModel, table=True):
    __tablename__ = "test_invalid_list_mode_item"
    __onesite__ = {"list_mode": "cards"}

    id: int | None = Field(default=None, primary_key=True)
    name: str


def _render_list_page(model_class: type[SQLModel], module_name: str) -> tuple[object, str]:
    result = get_model_fields(model_class, module_name)
    model = _build_model_dict(model_class.__name__, module_name, module_name, result)
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    rendered = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_list.tsx.j2"
    ).render(model=model)
    return model, rendered


def test_grid_list_mode_renders_responsive_cards_with_crud_controls():
    model, rendered = _render_list_page(GridItem, "grid_item")

    assert model.list_mode == "grid"
    assert 'data-page-region="grid-list"' in rendered
    assert "sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4" in rendered
    assert "renderGridValue('image', item)" in rendered
    assert 'data-grid-card' in rendered
    assert 'data-grid-create-card' in rendered
    assert "data.length === 0 && !hasPermission('c')" in rendered
    assert "handleCreate" in rendered
    assert 'data-grid-field="enabled"' in rendered
    assert 'grid-card-action-edit' in rendered
    assert 'grid-card-action-view' not in rendered
    assert "closest('button, input, a')" in rendered
    assert "handleEdit(item)" in rendered
    assert "requestDelete(item.id)" in rendered
    assert "<Table>" not in rendered


def test_list_mode_defaults_to_the_existing_table_layout():
    model, rendered = _render_list_page(DefaultListItem, "default_list_item")

    assert model.list_mode == "list"
    assert "<Table>" in rendered
    assert 'data-page-region="grid-list"' not in rendered


def test_invalid_list_mode_is_rejected():
    with pytest.raises(ValueError, match="Invalid list_mode"):
        get_model_fields(InvalidListModeItem, "invalid_list_mode_item")


def test_typed_list_mode_normalizes_when_explicitly_configured():
    assert normalize_onesite_config(OneSiteConfig(list_mode=ListMode.GRID)) == {
        "list_mode": "grid"
    }


def test_typed_list_mode_keeps_string_configuration_compatible():
    assert OneSiteConfig(list_mode="grid").list_mode is ListMode.GRID
