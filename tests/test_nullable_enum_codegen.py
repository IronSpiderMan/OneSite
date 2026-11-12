"""Regression coverage for enum fields in generated views."""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from onesite.codegen.i18n import generate_locale_files
from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict
from onesite.codegen.phases.relationships import phase_resolve_relationships
from onesite.codegen.render import create_template_environment


class AuthType(str, Enum):
    password = "password"
    token = "token"
    __i18n__ = {"zh": {"password": "密码", "token": "令牌"}}


class Connector(SQLModel, table=True):
    __tablename__ = "test_nullable_enum_connector"
    __onesite__ = {"translations": {"zh": {"enums": {"auth_type": {"password": "账号密码"}}}}}

    id: Optional[int] = Field(default=None, primary_key=True)
    auth_type: Optional[AuthType] = Field(default=None, nullable=True)
    auth_types: list[AuthType] = Field(default_factory=list, sa_column=Column(JSON))
    is_enabled: bool = True
    last_connected_at: datetime | None = None


class EnumDevice(SQLModel, table=True):
    __tablename__ = "test_enum_device"

    id: Optional[int] = Field(default=None, primary_key=True)
    connector_id: int = Field(foreign_key="test_nullable_enum_connector.id")


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


def test_detail_foreign_key_card_uses_target_model_translations(tmp_path):
    connector, device = phase_resolve_relationships([
        _build_model_dict("Connector", "connector", Connector.__tablename__, get_model_fields(Connector, "connector")),
        _build_model_dict("EnumDevice", "enum_device", "enum_device", get_model_fields(EnumDevice, "enum_device")),
    ])
    generate_locale_files([connector, device], tmp_path)
    zh = json.loads((tmp_path / "zh.json").read_text(encoding="utf-8"))
    enums = zh["models"]["connector"]["enums"]
    assert enums["auth_type"]["password"] == "账号密码"
    assert enums["auth_types"]["password"] == "密码"

    detail_page = create_template_environment("industrial").get_template(
        "frontend_page_detail.tsx.j2"
    ).render(model=device)
    assert "t(`models.connector.enums.auth_type.${connectorData.auth_type}`, { defaultValue: String(connectorData.auth_type) })" in detail_page
    assert "connectorData.auth_type != null ?" in detail_page
    assert "connectorData.auth_types.map(" in detail_page
    assert "t(`models.connector.enums.auth_types.${v}`, { defaultValue: String(v) })" in detail_page
    assert "connectorData.is_enabled == null ? '-' : (connectorData.is_enabled ? 'Yes' : 'No')" in detail_page
    assert "formatDateTime(connectorData.last_connected_at, timeZone)" in detail_page
