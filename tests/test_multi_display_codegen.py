"""Regression coverage for selectable multi-item collection displays."""

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict
from onesite.config import (
    MultiDisplayConfig,
    MultiDisplayFieldConfig,
    OneSiteConfig,
    normalize_onesite_config,
)


class MultiDisplayCamera(SQLModel, table=True):
    __tablename__ = "test_multi_display_camera"
    __onesite__ = {
        "multi_display": {
            "fields": [
                "snapshot_image",
                {"field": "stream_url", "renderer": "video", "span": 2},
                "description",
            ],
            "label_field": "name",
            "default_view": "multi",
            "max_selected": 4,
            "columns": 2,
        }
    }

    id: int | None = Field(default=None, primary_key=True)
    name: str
    snapshot_image: str | None = None
    stream_url: str | None = Field(
        default=None,
        sa_column_kwargs={
            "info": {
                "site_props": {
                    "component": "video_stream",
                    "stream": {"autoplay": True, "muted": True},
                }
            }
        },
    )
    description: str | None = None


class InvalidMultiDisplayField(SQLModel, table=True):
    __tablename__ = "test_invalid_multi_display_field"
    __onesite__ = {"multi_display": {"fields": ["missing"]}}

    id: int | None = Field(default=None, primary_key=True)
    name: str


class InvalidMultiDisplayRenderer(SQLModel, table=True):
    __tablename__ = "test_invalid_multi_display_renderer"
    __onesite__ = {
        "multi_display": {
            "fields": [{"field": "name", "renderer": "video"}],
        }
    }

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


def test_multi_display_config_is_normalized_and_rendered_with_separate_selection():
    model, rendered = _render_list_page(MultiDisplayCamera, "multi_display_camera")

    assert model.multi_display["label_field"] == "name"
    assert model.multi_display["fields"][0]["renderer"] == "image"
    assert model.multi_display["fields"][1]["renderer"] == "video"
    assert model.multi_display["fields"][2]["renderer"] == "text"
    assert model.multi_display["fields"][1]["stream_autoplay"] is True
    assert "const [displayItems, setDisplayItems]" in rendered
    assert "const [selectedIds, setSelectedIds]" in rendered
    assert 'data-page-region="multi-display"' not in rendered
    assert "<MultiDisplayView" in rendered
    assert "<VideoStreamPlayer" in rendered
    assert "viewMode === 'multi'" in rendered
    assert "<Table>" in rendered


def test_multi_display_rejects_unknown_fields_and_incompatible_renderers():
    with pytest.raises(ValueError, match="unknown field 'missing'"):
        get_model_fields(InvalidMultiDisplayField, "invalid_multi_display_field")
    with pytest.raises(ValueError, match="cannot use renderer 'video'"):
        get_model_fields(InvalidMultiDisplayRenderer, "invalid_multi_display_renderer")


def test_typed_multi_display_configuration_normalizes_to_model_metadata():
    config = OneSiteConfig(
        multi_display=MultiDisplayConfig(
            fields=[
                "snapshot_image",
                MultiDisplayFieldConfig(field="stream_url", renderer="video", span=2),
            ],
            label_field="name",
        )
    )

    assert config.multi_display is not None
    assert config.multi_display.max_selected == 4
    assert config.multi_display.fields[1].renderer == "video"
    normalized = normalize_onesite_config(config)
    assert normalized is not None
    assert normalized["multi_display"]["fields"][1]["renderer"] == "video"
