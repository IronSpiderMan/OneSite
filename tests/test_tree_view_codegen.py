"""Regression coverage for the generated self-referencing tree view."""

from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict
from onesite.codegen.phases.relationships import phase_resolve_relationships


class TreeItem(SQLModel, table=True):
    __tablename__ = "test_tree_item"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    parent_id: Optional[int] = Field(default=0, foreign_key="test_tree_item.id")


class TestTreeFolder(SQLModel, table=True):
    __test__ = False
    __tablename__ = "test_tree_folder"
    __onesite__ = {
        "tree_view": {
            "leaf": {
                "model": "TestTreeDocument",
                "parent_field": "folder_id",
                "label_field": "title",
            }
        }
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    parent_id: Optional[int] = Field(default=None, foreign_key="test_tree_folder.id")


class TestTreeDocument(SQLModel, table=True):
    __test__ = False
    __tablename__ = "test_tree_document"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    folder_id: int = Field(foreign_key="test_tree_folder.id")


def test_tree_view_has_hierarchy_cues_and_accessible_node_actions() -> None:
    result = get_model_fields(TreeItem, "tree_item")
    model = _build_model_dict("TreeItem", "tree_item", "tree_item", result)
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    page = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_list.tsx.j2"
    ).render(model=model)

    assert model.is_tree is True
    assert "CornerDownRight, Folder, FolderOpen" in page
    assert "pointer-events-none absolute top-0 bottom-0 w-px bg-border" in page
    assert "const hasLoadedChildren = Object.prototype.hasOwnProperty.call(childrenMap, node.id);" in page
    assert "const isLeaf = hasLoadedChildren && !isLoading" in page
    assert "disabled={isLeaf}" in page
    assert 'aria-label="Add child"' in page
    assert "{childTotal}" in page


def test_tree_view_renders_records_from_a_configured_leaf_model() -> None:
    models = []
    for model_class, module_name in (
        (TestTreeFolder, "tree_folder"),
        (TestTreeDocument, "tree_document"),
    ):
        result = get_model_fields(model_class, module_name)
        models.append(
            _build_model_dict(
                model_class.__name__, module_name, module_name, result,
                table_name=model_class.__tablename__,
            )
        )
    phase_resolve_relationships(models)
    folder = models[0]
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    page = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_list.tsx.j2"
    ).render(model=folder)

    assert folder.is_tree is True
    assert folder.tree_leaf["model"] == "TestTreeDocument"
    assert folder.tree_leaf["parent_field"] == "folder_id"
    assert "TreeLeafService.getTestTreeDocuments" in page
    assert 'data-tree-node-kind="leaf"' in page
    assert "leaf.title" in page
    assert "loadMoreLeaves" in page
