"""Regression coverage for human-readable, string-safe FK labels."""

from pathlib import Path
from typing import Optional

import pytest
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict
from onesite.codegen.phases.relationships import phase_resolve_relationships


class NumericSearchTarget(SQLModel, table=True):
    __tablename__ = "numeric_search_target"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    group_id: int = Field(
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}}
    )


class NumericSearchSource(SQLModel, table=True):
    __tablename__ = "numeric_search_source"

    id: Optional[int] = Field(default=None, primary_key=True)
    target_id: int = Field(foreign_key="numeric_search_target.id")


class ExplicitLabelTarget(SQLModel, table=True):
    __tablename__ = "explicit_label_target"
    __onesite__ = {"label_field": "code"}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    code: int


class ExplicitLabelSource(SQLModel, table=True):
    __tablename__ = "explicit_label_source"

    id: Optional[int] = Field(default=None, primary_key=True)
    target_id: int = Field(foreign_key="explicit_label_target.id")


def _resolve(*model_classes):
    definitions = []
    for model_class in model_classes:
        module = model_class.__tablename__
        definitions.append(
            _build_model_dict(
                model_class.__name__,
                module,
                module,
                get_model_fields(model_class, module),
            )
        )
    phase_resolve_relationships(definitions)
    return {model.name: model for model in definitions}


def _crud_template():
    template_dir = (
        Path(__file__).parents[1]
        / "src"
        / "onesite"
        / "templates"
        / "codegen"
    )
    return Environment(loader=FileSystemLoader(template_dir)).get_template("crud.py.j2")


def test_numeric_search_filter_does_not_become_fk_label_when_name_exists():
    models = _resolve(NumericSearchTarget, NumericSearchSource)
    source = models["NumericSearchSource"]
    target_fk = next(fk for fk in source.foreign_keys if fk["name"] == "target_id")

    assert models["NumericSearchTarget"].search_field == "group_id"
    assert target_fk["label_field"] == "name"


def test_generated_fk_labels_are_always_converted_to_strings():
    source = _resolve(ExplicitLabelTarget, ExplicitLabelSource)["ExplicitLabelSource"]
    target_fk = next(fk for fk in source.foreign_keys if fk["name"] == "target_id")
    rendered = _crud_template().render(model=source)

    assert target_fk["label_field"] == "code"
    assert "target_id_map[obj.id] = str(label) if label is not None else str(obj.id)" in rendered


def test_explicit_unknown_label_field_is_rejected():
    class InvalidLabelTarget(SQLModel, table=True):
        __tablename__ = "invalid_label_target"
        __onesite__ = {"label_field": "missing"}

        id: Optional[int] = Field(default=None, primary_key=True)

    class InvalidLabelSource(SQLModel, table=True):
        __tablename__ = "invalid_label_source"

        id: Optional[int] = Field(default=None, primary_key=True)
        target_id: int = Field(foreign_key="invalid_label_target.id")

    with pytest.raises(ValueError, match="label_field 'missing' does not exist"):
        _resolve(InvalidLabelTarget, InvalidLabelSource)
