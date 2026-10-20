"""Regression coverage for nullable enum fields in generated views."""

from enum import Enum
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict


class AuthType(str, Enum):
    password = "password"
    token = "token"


class Connector(SQLModel, table=True):
    __tablename__ = "test_nullable_enum_connector"

    id: Optional[int] = Field(default=None, primary_key=True)
    auth_type: Optional[AuthType] = Field(default=None, nullable=True)


def test_nullable_enum_renders_empty_state_instead_of_an_i18n_key():
    result = get_model_fields(Connector, "connector")
    model = _build_model_dict("Connector", "connector", "connector", result)
    template_dir = (
        Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    )
    environment = Environment(loader=FileSystemLoader(template_dir))

    list_page = environment.get_template("frontend_page_list.tsx.j2").render(model=model)
    detail_page = environment.get_template("frontend_page_detail.tsx.j2").render(model=model)

    assert "item.auth_type != null ?" in list_page
    assert "currentItem.auth_type != null ?" in detail_page
    assert "enums.auth_type.${item.auth_type}" in list_page
    assert "enums.auth_type.${currentItem.auth_type}" in detail_page
