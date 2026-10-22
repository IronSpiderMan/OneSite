"""Regression coverage for aggregate-style inline relationship editing."""

import ast
from pathlib import Path
from typing import Optional

import pytest
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel
from sqlalchemy import Column, JSON

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict
from onesite.codegen.phases import generate as generate_phase
from onesite.codegen.phases.relationships import phase_resolve_relationships


class InlineA(SQLModel, table=True):
    __tablename__ = "test_inline_a"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class InlineB(SQLModel, table=True):
    __tablename__ = "test_inline_b"
    __onesite__ = {"standalone": False}

    id: Optional[int] = Field(default=None, primary_key=True)
    inline_a_id: int = Field(
        foreign_key="test_inline_a.id",
        sa_column_kwargs={
            "info": {
                "site_props": {
                    "is_search_field": True,
                    "target_service": "inline_a",
                    "reverse": {"editor": "inline", "on_remove": "delete"},
                }
            }
        },
    )
    region_id: Optional[int] = Field(
        default=None,
        foreign_key="test_inline_c.id",
        sa_column_kwargs={"info": {"site_props": {"target_service": "inline_c"}}},
    )
    title: str = Field(
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}}
    )
    amount: int = 0


class InlineC(SQLModel, table=True):
    __tablename__ = "test_inline_c"
    __onesite__ = {"standalone": False}

    id: Optional[int] = Field(default=None, primary_key=True)
    label: str


class InlineACLink(SQLModel, table=True):
    __tablename__ = "test_inline_ac_link"
    __onesite__ = {
        "is_link_table": True,
        "m2m": {
            "directions": [
                {
                    "from": "inline_a",
                    "to": "inline_c",
                    "editor": "inline",
                    "allow_existing": False,
                }
            ]
        },
    }

    inline_a_id: int = Field(
        foreign_key="test_inline_a.id",
        primary_key=True,
        sa_column_kwargs={"info": {"site_props": {"target_service": "inline_a"}}},
    )
    inline_c_id: int = Field(
        foreign_key="test_inline_c.id",
        primary_key=True,
        sa_column_kwargs={"info": {"site_props": {"target_service": "inline_c"}}},
    )


def _models():
    definitions = []
    for cls, module in (
        (InlineA, "inline_a"),
        (InlineB, "inline_b"),
        (InlineC, "inline_c"),
        (InlineACLink, "inline_ac_link"),
    ):
        result = get_model_fields(cls, module)
        definitions.append(_build_model_dict(cls.__name__, module, module, result))
    phase_resolve_relationships(definitions)
    return {model.name: model for model in definitions}


def _template(name: str):
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    return Environment(loader=FileSystemLoader(template_dir)).get_template(name)


def test_inline_relation_metadata_and_standalone_flag():
    models = _models()
    a = models["InlineA"]

    reverse = next(rel for rel in a.reverse_foreign_keys if rel["source_model"] == "InlineB")
    assert reverse["editor"] == "inline"
    assert reverse["write_name"] == "inline_bs"
    assert reverse["on_remove"] == "delete"
    assert [field["name"] for field in reverse["inline_fields"]] == ["region_id", "title", "amount"]
    region_field = next(field for field in reverse["inline_schema"]["fields"] if field["name"] == "region_id")
    assert region_field["kind"] == "foreign_key"
    assert region_field["foreignKey"] == {
        "targetModel": "InlineC",
        "targetService": "inline_c",
        "labelField": "label",
    }

    m2m = next(rel for rel in a.m2m_fields if rel["target_model"] == "InlineC")
    assert m2m["editor"] == "inline"
    assert m2m["write_name"] == "inline_cs"
    assert m2m["on_remove"] == "unlink"
    assert models["InlineB"].standalone is False
    assert models["InlineC"].standalone is False


def test_inline_schema_and_crud_are_generated_as_valid_python():
    a = _models()["InlineA"]
    schema = _template("schema.py.j2").render(model=a)
    crud = _template("crud.py.j2").render(model=a)
    api = _template("api.py.j2").render(model=a)

    ast.parse(schema)
    ast.parse(crud)
    ast.parse(api)
    assert "class InlineAInlineInlineBItem(SQLModel):" in schema
    assert "inline_bs: Optional[List[InlineAInlineInlineBItem]]" in schema
    assert "inline_cs: Optional[List[InlineAInlineInlineCItem]]" in schema
    assert "async def _sync_inline_inline_bs(" in crud
    assert "await session.delete(child)" in crud
    assert "async def _sync_inline_inline_cs(" in crud
    assert "await session.delete(link)" in crud
    assert "def _check_inline_relation_permissions" in api
    assert "await _check_inline_relation_permissions(inlinea_in, current_user, updating=False, session=session)" in api


def test_inline_editors_are_rendered_in_create_and_list_forms():
    a = _models()["InlineA"]
    for template_name, page_edit in (
        ("frontend_page_list.tsx.j2", False),
        ("frontend_page_create.tsx.j2", True),
    ):
        a.page_edit = page_edit
        rendered = _template(template_name).render(model=a)
        assert 'name="inline_bs"' in rendered
        assert 'name="inline_cs"' in rendered
        assert "<JsonModelArrayEditor" in rendered


def test_inline_reverse_relation_can_match_typed_dict_table_ui():
    models = list(_models().values())
    child = next(model for model in models if model.name == "InlineB")
    child.foreign_keys[0].reverse = {
        "editor": "inline",
        "layout": "table",
        "on_remove": "delete",
    }
    phase_resolve_relationships(models)

    parent = next(model for model in models if model.name == "InlineA")
    relation = next(
        rel for rel in reversed(parent.reverse_foreign_keys)
        if rel["source_model"] == "InlineB"
    )
    assert relation["inline_layout"] == "table"

    for template_name in (
        "frontend_page_create.tsx.j2",
        "frontend_page_list.tsx.j2",
        "frontend_page_detail.tsx.j2",
    ):
        parent.page_edit = template_name != "frontend_page_list.tsx.j2"
        rendered = _template(template_name).render(model=parent)
        relation_fragment = rendered.split('name="inline_bs"', 1)[1]
        assert "<JsonModelTableEditor" in relation_fragment
        assert 'collectionKind="array"' in relation_fragment
        assert "foreignKeyLoaders={{" in relation_fragment


def test_inline_table_preserves_conditional_json_array_fields():
    class ConditionalParent(SQLModel, table=True):
        __tablename__ = "test_conditional_inline_parent"

        id: Optional[int] = Field(default=None, primary_key=True)

    class ConditionalChild(SQLModel, table=True):
        __tablename__ = "test_conditional_inline_child"

        id: Optional[int] = Field(default=None, primary_key=True)
        parent_id: int = Field(
            foreign_key="test_conditional_inline_parent.id",
            sa_column_kwargs={"info": {"site_props": {
                "target_service": "conditional_parent",
                "reverse": {"editor": "inline", "layout": "table"},
            }}},
        )
        dtype: str
        enum_values: Optional[list[str]] = Field(
            default=None,
            sa_column=Column(
                JSON,
                info={"site_props": {
                    "visible_when": {"dtype": ["enum"]},
                    "required_when": {"dtype": ["enum"]},
                    "clear_when_hidden": True,
                }},
            ),
        )

    definitions = []
    for cls, module in (
        (ConditionalParent, "conditional_parent"),
        (ConditionalChild, "conditional_child"),
    ):
        result = get_model_fields(cls, module)
        definitions.append(_build_model_dict(cls.__name__, module, module, result))
    phase_resolve_relationships(definitions)

    parent = next(model for model in definitions if model.name == "ConditionalParent")
    relation = parent.reverse_foreign_keys[0]
    enum_values = next(
        field for field in relation["inline_schema"]["fields"]
        if field["name"] == "enum_values"
    )
    assert enum_values["kind"] == "array"
    assert enum_values["visibleWhen"] == {"dtype": ["enum"]}
    assert enum_values["requiredWhen"] == {"dtype": ["enum"]}
    assert enum_values["clearWhenHidden"] is True


def test_inline_detail_editor_keeps_m2m_editing_in_the_detail_form():
    a = _models()["InlineA"]
    a.page_edit = True

    rendered = _template("frontend_page_detail.tsx.j2").render(model=a)

    assert "const [activeTab, setActiveTab] = useState('detail');" in rendered
    assert "activeTab === 'reverse-fk-inline_bs'" in rendered
    m2m_name = next(rel["name"] for rel in a.m2m_fields if rel["target_model"] == "InlineC")
    assert f"activeTab === 'm2m-{m2m_name}'" not in rendered
    assert 'name="inline_bs"' in rendered
    assert 'name="inline_cs"' in rendered
    assert rendered.count("showJsonMode={false}") == 2
    detail_form = rendered.split('<form id="detail-edit-form"', 1)[1].split("</form>", 1)[0]
    assert 'name="inline_bs"' not in detail_form
    assert 'name="inline_cs"' in detail_form


def test_inline_editor_foreign_keys_render_searchable_select_loaders():
    a = _models()["InlineA"]
    for template_name, page_edit in (
        ("frontend_page_create.tsx.j2", True),
        ("frontend_page_list.tsx.j2", False),
        ("frontend_page_detail.tsx.j2", True),
    ):
        a.page_edit = page_edit
        rendered = _template(template_name).render(model=a)
        assert "foreignKeyLoaders={{" in rendered
        assert "InlineBsRegionIdInlineFieldService.getInlineCs" in rendered
        assert "import * as InlineBsRegionIdInlineFieldService from '../../services/inline_c';" in rendered


def test_detail_relationship_pages_have_adjustable_page_sizes():
    a = _models()["InlineA"]
    rendered = _template("frontend_page_detail.tsx.j2").render(model=a)

    reverse_fk = next(rel for rel in a.reverse_foreign_keys if rel["source_model"] == "InlineB")
    m2m = next(rel for rel in a.m2m_fields if rel["target_model"] == "InlineC")

    for relation_name in (reverse_fk["name"], m2m["name"]):
        assert f"const [{relation_name}Size," in rendered
        assert f"value={{String({relation_name}Size)}}" in rendered
        assert f"Total / {relation_name}Size" in rendered

    assert "size: number =" in rendered
    assert "/ 5)" not in rendered


def test_reverse_fk_detail_uses_child_search_fields_with_live_updates():
    a = _models()["InlineA"]
    rendered = _template("frontend_page_detail.tsx.j2").render(model=a)
    reverse_fk = next(rel for rel in a.reverse_foreign_keys if rel["source_model"] == "InlineB")

    assert [field["name"] for field in reverse_fk["source_search_fields"]] == ["title"]
    assert "const [inline_bsSearchValues, setInlineBSearchValues]" in rendered
    assert "...buildInlineBSearchFilters(searchValues)" in rendered
    assert "}, 300);" in rendered
    assert "}, [inline_bsSearchValues]);" in rendered
    assert "setInlineBSearchValues((current)" in rendered
    assert "setInlineBSearchValues({})" not in rendered
    assert "t('common.filters', 'Filters')" not in rendered
    assert "mb-4 w-full max-w-sm" in rendered


def test_searchable_foreign_key_is_supported_through_backend_layers():
    b = _models()["InlineB"]
    api = _template("api.py.j2").render(model=b)
    service = _template("service.py.j2").render(model=b)
    crud = _template("crud.py.j2").render(model=b)

    ast.parse(api)
    ast.parse(service)
    ast.parse(crud)
    assert "inline_a_id: Optional[int] = Query(None" in api
    assert "inline_a_id: Optional[int] = None" in service
    assert "InlineB.inline_a_id == inline_a_id" in crud


def test_selector_label_search_is_filtered_without_enabling_list_search():
    from sqlalchemy import select
    from sqlmodel import Session, col, create_engine

    models = _models()
    target = models["InlineC"]
    label = next(field for field in target.fields if field.name == "label")
    label.is_search_field = False
    phase_resolve_relationships(list(models.values()))
    assert label.is_selector_filter
    assert not label.is_search_field

    for template_name in ("api.py.j2", "service.py.j2", "crud.py.j2"):
        rendered = _template(template_name).render(model=target)
        tree = ast.parse(rendered)
        assert "label: Optional[str]" in rendered
        if template_name != "crud.py.j2":
            assert "label=label" in rendered
            continue

        apply_filters = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_apply_filters")
        namespace = {"InlineC": InlineC, "Optional": Optional, "col": col}
        exec(compile(ast.Module(body=[apply_filters], type_ignores=[]), "<filters>", "exec"), namespace)
        engine = create_engine("sqlite://")
        InlineC.__table__.create(engine)
        with Session(engine) as session:
            session.add_all([InlineC(label="device0000"), InlineC(label="device0525")])
            session.commit()
            statement = namespace["_apply_filters"](select(InlineC), label="DEVICE0000")
            assert [item.label for item in session.execute(statement).scalars()] == ["device0000"]
            statement = namespace["_apply_filters"](select(InlineC), label="missing")
            assert list(session.execute(statement).scalars()) == []


def test_non_standalone_model_keeps_service_but_skips_pages(monkeypatch, tmp_path):
    b = _models()["InlineB"]
    generated_templates = []

    def capture(template_name, context, output_path):
        generated_templates.append(template_name)

    monkeypatch.setattr(generate_phase, "generate_file", capture)
    generate_phase._generate_regular_model(b, tmp_path, tmp_path / "backend")

    assert "frontend_service.ts.j2" in generated_templates
    assert "frontend_store.ts.j2" not in generated_templates
    assert "frontend_page_list.tsx.j2" not in generated_templates
    assert "frontend_page_detail.tsx.j2" not in generated_templates


def test_embedded_reverse_relation_marks_child_for_reusable_list_page():
    models = list(_models().values())
    node = next(model for model in models if model.name == "InlineB")
    node.foreign_keys[0].reverse = {"editor": "embedded", "on_remove": "delete"}

    phase_resolve_relationships(models)

    parent = next(model for model in models if model.name == "InlineA")
    relation = next(rel for rel in reversed(parent.reverse_foreign_keys) if rel["source_model"] == "InlineB")
    assert relation["editor"] == "embedded"
    assert relation["allow_existing"] is True
    assert node["has_embedded_page"] is True


def test_embedded_reverse_uses_fixed_height_only_on_embedded_tab():
    models = list(_models().values())
    node = next(model for model in models if model.name == "InlineB")
    node.foreign_keys[0].reverse = {"editor": "embedded", "on_remove": "delete"}

    phase_resolve_relationships(models)

    parent = next(model for model in models if model.name == "InlineA")
    detail = _template("frontend_page_detail.tsx.j2").render(model=parent)
    assert "const isEmbeddedTab" in detail
    assert "isEmbeddedTab ? '!flex !h-full" in detail
    assert "isEmbeddedTab ? '!flex-1 !min-h-0'" in detail


def test_embedded_reverse_relation_can_attach_existing_children():
    models = list(_models().values())
    node = next(model for model in models if model.name == "InlineB")
    node.foreign_keys[0].reverse = {"editor": "embedded", "allow_existing": True}

    phase_resolve_relationships(models)

    parent = next(model for model in models if model.name == "InlineA")
    child = next(model for model in models if model.name == "InlineB")
    detail = _template("frontend_page_detail.tsx.j2").render(model=parent)
    embedded = _template("frontend_page_list.tsx.j2").render(model=child)

    assert 'allowAttachExisting={true}' in detail
    assert 'relationField="inline_a_id"' in detail
    assert "relationValue={parseInt(id!)}" in detail
    assert "const loadAttachExistingOptions" in embedded
    assert "updateInlineB(recordId, { [relationField]: relationValue })" in embedded
    assert "t('common.add_existing', 'Add existing')" in embedded


def test_embedded_page_with_one_search_field_keeps_create_action():
    models = list(_models().values())
    node = next(model for model in models if model.name == "InlineB")
    node.foreign_keys[0].reverse = {"editor": "embedded", "allow_existing": True}
    phase_resolve_relationships(models)

    child = next(model for model in models if model.name == "InlineB")
    for field in child.fields:
        if field.name != "title":
            field.is_search_field = False

    embedded = _template("frontend_page_list.tsx.j2").render(model=child)

    assert "{embedded && (" in embedded
    assert "hasPermission('c')" in embedded
    assert "className={embedded ? 'rounded-md border bg-card p-4" in embedded


def test_standalone_embedded_model_generates_both_page_variants(monkeypatch, tmp_path):
    model = _models()["InlineB"]
    model.standalone = True
    model.has_embedded_page = True
    generated_paths = []

    def capture(template_name, context, output_path, *args):
        generated_paths.append(Path(output_path))

    monkeypatch.setattr(generate_phase, "generate_file", capture)
    monkeypatch.setattr(generate_phase, "generate_theme_file", capture)

    generate_phase._generate_regular_model(model, tmp_path, tmp_path / "backend")

    frontend_pages = {
        path.name
        for path in generated_paths
        if "pages" in path.parts and path.parent.name == "inline_b"
    }
    assert frontend_pages == {"embedded.tsx", "index.tsx", "detail.tsx"}
    assert sum(path.name == "useInlineBStore.ts" for path in generated_paths) == 1


def test_nullify_requires_a_nullable_reverse_foreign_key():
    models = list(_models().values())
    b = next(model for model in models if model.name == "InlineB")
    b.foreign_keys[0].reverse = {"editor": "inline", "on_remove": "nullify"}

    with pytest.raises(ValueError, match="foreign key is not Optional"):
        phase_resolve_relationships(models)
