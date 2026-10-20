"""Regression coverage for nullable foreign keys on generated detail pages."""

from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict
from onesite.codegen.phases.relationships import phase_resolve_relationships


class NullableFkGroup(SQLModel, table=True):
    __tablename__ = "test_nullable_fk_group"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class NullableFkMember(SQLModel, table=True):
    __tablename__ = "test_nullable_fk_member"

    id: Optional[int] = Field(default=None, primary_key=True)
    group_id: Optional[int] = Field(
        default=None,
        foreign_key="test_nullable_fk_group.id",
    )


def test_nullable_foreign_key_renders_empty_state_instead_of_loading_forever():
    definitions = []
    for model_class, module_name in (
        (NullableFkGroup, "nullable_fk_group"),
        (NullableFkMember, "nullable_fk_member"),
    ):
        result = get_model_fields(model_class, module_name)
        definitions.append(
            _build_model_dict(
                model_class.__name__, module_name, module_name, result
            )
        )
    phase_resolve_relationships(definitions)
    member = next(model for model in definitions if model.name == "NullableFkMember")

    template_dir = (
        Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    )
    detail_page = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_detail.tsx.j2"
    ).render(model=member)

    target_model = member.foreign_keys[0].target_model
    assert f"set{target_model}Data(null);" in detail_page
    assert "item.group_id !== null && item.group_id !== undefined" in detail_page
    assert (
        "currentItem.group_id === null || currentItem.group_id === undefined"
        in detail_page
    )
    assert "{t('common.no_result')}" in detail_page
    assert "nullable_fk_groupData?.name" in detail_page


def test_single_item_service_enriches_foreign_key_labels():
    definitions = []
    for model_class, module_name in (
        (NullableFkGroup, "nullable_fk_group"),
        (NullableFkMember, "nullable_fk_member"),
    ):
        result = get_model_fields(model_class, module_name)
        definitions.append(
            _build_model_dict(model_class.__name__, module_name, module_name, result)
        )
    phase_resolve_relationships(definitions)
    member = next(model for model in definitions if model.name == "NullableFkMember")
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    environment = Environment(loader=FileSystemLoader(template_dir))

    crud = environment.get_template("crud.py.j2").render(model=member)
    service = environment.get_template("service.py.j2").render(model=member)
    user_crud = environment.get_template("user_crud.py.j2").render(model=member)
    user_service = environment.get_template("user_service.py.j2").render(model=member)

    assert "async def get_with_fk_labels(" in crud
    assert 'item_dict["group_id_label"] = group_id_map.get(fk_id)' in crud
    assert "obj = await crud.get_with_fk_labels(session, id)" in service
    assert "async def get_with_fk_labels(" in user_crud
    assert 'item_dict["group_id_label"] = None' in user_crud
    assert "obj = await crud.get_with_fk_labels(session, id)" in user_service
