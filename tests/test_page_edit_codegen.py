"""Regression coverage for full-page editing navigation."""

from pathlib import Path
from typing import Optional

import pytest
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict


class PageEditableItem(SQLModel, table=True):
    __tablename__ = "test_page_editable_item"
    __onesite__ = {"page_edit": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    is_enabled: bool = False


class AutoRefreshPageEditableItem(SQLModel, table=True):
    __tablename__ = "test_auto_refresh_page_editable_item"
    __onesite__ = {"page_edit": True, "refresh_interval": 5000}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class DrawerEditableItem(SQLModel, table=True):
    __tablename__ = "test_drawer_editable_item"
    __onesite__ = {"edit_mode": "drawer"}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class InplaceEditableItem(SQLModel, table=True):
    __tablename__ = "test_inplace_editable_item"
    __onesite__ = {"edit_mode": "inplace_edit"}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    is_enabled: bool = False


class InvalidEditModeItem(SQLModel, table=True):
    __tablename__ = "test_invalid_edit_mode_item"
    __onesite__ = {"edit_mode": "sidebar"}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class InvalidInplaceGridItem(SQLModel, table=True):
    __tablename__ = "test_invalid_inplace_grid_item"
    __onesite__ = {"edit_mode": "inplace_edit", "list_mode": "grid"}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


def test_full_page_editor_repopulates_form_when_route_item_changes():
    result = get_model_fields(PageEditableItem, "page_editable_item")
    model = _build_model_dict(
        "PageEditableItem", "page_editable_item", "page_editable_item", result
    )
    template_dir = (
        Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    )
    detail_page = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_detail.tsx.j2"
    ).render(model=model)

    assert "const autoEditedItemId = useRef<string | null>(null);" in detail_page
    assert "String(currentItem.id) === id" in detail_page
    assert "autoEditedItemId.current !== id" in detail_page
    assert "autoEditedItemId.current = id;" in detail_page
    assert "}, [currentItem, id, searchParams]);" in detail_page
    assert "const hasAutoEdited = useRef(false);" not in detail_page


def test_page_edit_action_regions_wrap_instead_of_overflowing():
    result = get_model_fields(PageEditableItem, "page_editable_item")
    model = _build_model_dict(
        "PageEditableItem", "page_editable_item", "page_editable_item", result
    )
    template_dir = (
        Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    )
    environment = Environment(loader=FileSystemLoader(template_dir))

    detail_page = environment.get_template("frontend_page_detail.tsx.j2").render(model=model)
    create_page = environment.get_template("frontend_page_create.tsx.j2").render(model=model)

    assert 'data-page-region="page-actions"' in detail_page
    assert "flex-wrap items-center justify-end gap-2" in detail_page
    assert 'data-page-region="page-controls"' in create_page
    assert "flex-wrap items-center justify-end gap-3" in create_page


def test_full_page_cud_actions_show_pending_feedback():
    result = get_model_fields(PageEditableItem, "page_editable_item")
    model = _build_model_dict(
        "PageEditableItem", "page_editable_item", "page_editable_item", result
    )
    template_dir = (
        Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    )
    environment = Environment(loader=FileSystemLoader(template_dir))

    detail_page = environment.get_template("frontend_page_detail.tsx.j2").render(model=model)
    create_page = environment.get_template("frontend_page_create.tsx.j2").render(model=model)

    assert "const [isSaving, setIsSaving] = useState(false);" in detail_page
    assert 'disabled={isSaving} onClick={handleEditSubmit(onEditSave)}' in detail_page
    assert "t('common.saving', 'Saving...')" in detail_page
    assert "await updateItem(currentItem!.id, updatePayload, { refreshList: false });" in detail_page
    assert "await fetchItem(currentItem!.id);" not in detail_page
    assert 'disabled={submitting}' in create_page
    assert "t('common.saving', 'Saving...')" in create_page


def test_page_edit_boolean_field_matches_standard_field_layout():
    result = get_model_fields(PageEditableItem, "page_editable_item")
    model = _build_model_dict(
        "PageEditableItem", "page_editable_item", "page_editable_item", result
    )
    template_dir = (
        Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    )
    detail_page = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_detail.tsx.j2"
    ).render(model=model)

    assert 'htmlFor="edit-is_enabled">{t(' in detail_page
    assert 'className="flex h-10 items-center justify-end rounded-md border px-3"' in detail_page


def test_page_edit_groups_refresh_with_actions_and_pauses_it_while_editing():
    result = get_model_fields(AutoRefreshPageEditableItem, "auto_refresh_page_editable_item")
    model = _build_model_dict(
        "AutoRefreshPageEditableItem",
        "auto_refresh_page_editable_item",
        "auto_refresh_page_editable_item",
        result,
    )
    template_dir = (
        Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    )
    detail_page = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_detail.tsx.j2"
    ).render(model=model)

    assert 'data-page-region="page-controls"' in detail_page
    assert 'data-page-region="auto-refresh-controls"' in detail_page
    assert detail_page.index('data-page-region="auto-refresh-controls"') < detail_page.index(
        'data-page-region="page-actions"'
    )
    assert "if (autoRefresh && id && !isEditing)" in detail_page
    assert "[autoRefresh, refreshInterval, id, fetchItem, isEditing]" in detail_page
    assert "{!isEditing && (" in detail_page


def test_drawer_edit_mode_generates_a_right_side_editor_container():
    result = get_model_fields(DrawerEditableItem, "drawer_editable_item")
    model = _build_model_dict(
        "DrawerEditableItem", "drawer_editable_item", "drawer_editable_item", result
    )
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    list_page = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_list.tsx.j2"
    ).render(model=model)

    assert result.edit_mode == "drawer"
    assert model.page_edit is False
    assert "import { Drawer as EditContainer }" in list_page
    assert "<EditContainer" in list_page
    assert "navigate('/drawer_editable_items/new')" not in list_page


def test_inplace_edit_mode_generates_row_editor_and_keeps_modal_for_create():
    result = get_model_fields(InplaceEditableItem, "inplace_editable_item")
    model = _build_model_dict(
        "InplaceEditableItem", "inplace_editable_item", "inplace_editable_item", result
    )
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    list_page = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_list.tsx.j2"
    ).render(model=model)

    assert result.edit_mode == "inplace_edit"
    assert model.page_edit is False
    assert 'data-inplace-field="name"' in list_page
    assert "editingId === item.id && hasFieldPerm('name', 'u')" in list_page
    assert "onClick={() => void handleSubmit(onSubmit)()}" in list_page
    assert "onClick={handleCancelInplaceEdit}" in list_page
    assert "setEditingId(null);" in list_page
    assert "<EditContainer" in list_page
    assert "setIsModalOpen(false);" in list_page


def test_invalid_edit_mode_is_rejected():
    with pytest.raises(ValueError, match="Invalid edit_mode"):
        get_model_fields(InvalidEditModeItem, "invalid_edit_mode_item")


def test_inplace_edit_mode_rejects_non_table_lists():
    result = get_model_fields(InvalidInplaceGridItem, "invalid_inplace_grid_item")
    with pytest.raises(ValueError, match="paginated table list"):
        _build_model_dict(
            "InvalidInplaceGridItem",
            "invalid_inplace_grid_item",
            "invalid_inplace_grid_item",
            result,
        )
