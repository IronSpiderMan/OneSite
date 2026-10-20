"""Regression coverage for the multi-image field component."""

from pathlib import Path
from typing import List, Optional

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict


class Gallery(SQLModel, table=True):
    __tablename__ = "test_gallery"

    id: Optional[int] = Field(default=None, primary_key=True)
    images: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, info={"site_props": {"component": "images"}}),
    )


def test_images_component_generates_multi_image_uploader_and_galleries():
    result = get_model_fields(Gallery, "gallery")
    model = _build_model_dict("Gallery", "gallery", "gallery", result)
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    environment = Environment(loader=FileSystemLoader(template_dir))

    field = next(field for field in result.fields if field.name == "images")
    assert field.type == "List[str]"
    assert field.ui_type == "images"

    create_page = environment.get_template("frontend_page_create.tsx.j2").render(model=model)
    list_page = environment.get_template("frontend_page_list.tsx.j2").render(model=model)
    detail_page = environment.get_template("frontend_page_detail.tsx.j2").render(model=model)

    assert "import { ImagesUpload }" in create_page
    assert '<ImagesUpload id="images" value={Array.isArray(value) ? value : []} onChange={onChange} />' in create_page
    assert "item.images.length - 1" in list_page
    assert "currentItem.images.map" in detail_page


def test_images_upload_exposes_a_native_multi_file_input():
    component = (Path(__file__).parents[1] / "src" / "onesite" / "templates" / "frontend" / "src" / "components" / "ui" / "images-upload.tsx").read_text()

    assert 'Click or drag images here' in component
    assert 'className="absolute inset-0 h-full w-full cursor-pointer opacity-0"' in component
    assert 'multiple' in component
    assert 'id={id}' in component
    assert 'type="file"' in component
