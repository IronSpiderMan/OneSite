"""Regression coverage for parent/child foreign-key selectors."""

from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import ForeignKeyConstraint, PrimaryKeyConstraint
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict
from onesite.codegen.phases.relationships import phase_resolve_relationships


class CascadeA(SQLModel, table=True):
    __tablename__ = "cascade_a"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class CascadeB(SQLModel, table=True):
    __tablename__ = "cascade_b"

    id: Optional[int] = Field(default=None, primary_key=True)
    a_id: int = Field(foreign_key="cascade_a.id")
    name: str


class CascadeC(SQLModel, table=True):
    __tablename__ = "cascade_c"
    __onesite__ = {"page_edit": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    a_id: int = Field(foreign_key="cascade_a.id")
    b_id: int = Field(foreign_key="cascade_b.id")
    name: str


class CompositeA(SQLModel, table=True):
    __tablename__ = "composite_a"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class CompositeB(SQLModel, table=True):
    __tablename__ = "composite_b"
    __table_args__ = (
        PrimaryKeyConstraint("a_id", "name", name="pk_composite_b"),
    )

    a_id: int = Field(foreign_key="composite_a.id")
    name: str


class CompositeC(SQLModel, table=True):
    __tablename__ = "composite_c"
    __onesite__ = {"page_edit": True}
    __table_args__ = (
        ForeignKeyConstraint(
            ["a_id", "b_name"],
            ["composite_b.a_id", "composite_b.name"],
            name="fk_composite_c_b",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    a_id: int = Field(foreign_key="composite_a.id")
    b_name: str


def _models():
    definitions = []
    for cls, module in ((CascadeA, "cascade_a"), (CascadeB, "cascade_b"), (CascadeC, "cascade_c")):
        definitions.append(_build_model_dict(cls.__name__, module, module, get_model_fields(cls, module)))
    phase_resolve_relationships(definitions)
    return {model.name: model for model in definitions}


def _template(name: str):
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    return Environment(loader=FileSystemLoader(template_dir)).get_template(name)


def test_infers_and_renders_a_to_b_cascade_selector():
    model = _models()["CascadeC"]
    b_fk = next(fk for fk in model.foreign_keys if fk["name"] == "b_id")

    assert b_fk["cascade_parent_field"] == "a_id"
    assert b_fk["cascade_filter_field"] == "a_id"

    for template_name in ("frontend_page_create.tsx.j2", "frontend_page_detail.tsx.j2"):
        rendered = _template(template_name).render(model=model)
        assert "'a_id': parentId" in rendered
        assert "setValue('b_id', '')" in rendered or "setEditValue('b_id', '')" in rendered

    # List pages render the same form in modal edit mode.
    list_template = (Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen" / "frontend_page_list.tsx.j2").read_text()
    assert "cascade_parent_field" in list_template
    assert "setValue('{{ cascade_fk.name }}', '');" in list_template


def test_infers_composite_name_selector_and_persists_remote_name():
    definitions = []
    for cls, module in (
        (CompositeA, "composite_a"),
        (CompositeB, "composite_b"),
        (CompositeC, "composite_c"),
    ):
        definitions.append(_build_model_dict(cls.__name__, module, module, get_model_fields(cls, module)))
    phase_resolve_relationships(definitions)
    model = next(item for item in definitions if item.name == "CompositeC")
    field = next(item for item in model.fields if item.name == "b_name")

    assert field.composite_selector == {
        "target_table": "composite_b",
        "parent_field": "a_id",
        "filter_field": "a_id",
        "value_field": "name",
        "target_model": "CompositeB",
        "target_service": "composite_b",
        "label_field": "name",
    }

    create_page = _template("frontend_page_create.tsx.j2").render(model=model)
    detail_page = _template("frontend_page_detail.tsx.j2").render(model=model)
    model["page_edit"] = False
    model["edit_mode"] = "modal"
    list_page = _template("frontend_page_list.tsx.j2").render(model=model)
    for rendered in (create_page, detail_page, list_page):
        assert "'a_id': parentValue" in rendered
        assert "value: item.name" in rendered
        assert "getCompositeBs(1, 20, filters)" in rendered
        assert "b_name" in rendered

    target_model = next(item for item in definitions if item.name == "CompositeB")
    target_crud = _template("crud.py.j2").render(model=target_model)
    assert "if name:" in target_crud
    assert "CompositeB.name" in target_crud
