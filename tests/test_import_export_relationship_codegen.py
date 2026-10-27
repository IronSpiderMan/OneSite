"""CSV import/export configuration and relationship regression coverage."""

import ast
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict, _process_introspected_class
from onesite.codegen.phases.generate import _generate_custom_io_handler
from onesite.codegen.phases.relationships import phase_resolve_relationships


class CsvCategory(SQLModel, table=True):
    __tablename__ = "csv_category"
    __onesite__ = {
        "translations": {
            "en": {"fields": {"csv_items": "Products"}},
            "zh": {"fields": {"csv_items": "商品"}},
        },
        "exportable": {"reverse_foreign_keys": {"csv_items": "name"}},
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(unique=True, index=True)


class CsvTag(SQLModel, table=True):
    __tablename__ = "csv_tag"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(unique=True, index=True)


class CsvItem(SQLModel, table=True):
    __tablename__ = "csv_item"
    __onesite__ = {
        "import_key": "sku",
        "translations": {
            "en": {"fields": {"name": "Product name", "category_id": "Category"}},
            "zh": {"fields": {"sku": "商品编码", "name": "商品名称", "category_id": "分类"}},
        },
        "importable": {
            "fields": ["sku", "name", "category_id"],
            "foreign_keys": {"category_id": "title"},
            "m2m": {"tags": "title"},
        },
        "exportable": {
            "fields": ["sku", "name", "category_id", "internal_note"],
            "foreign_keys": {"category_id": "title"},
            "m2m": {"tags": "title"},
        },
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    sku: str = Field(
        unique=True,
        index=True,
        sa_column_kwargs={"info": {"site_props": {"translations": {"en": "SKU"}}}},
    )
    name: str = Field(
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}}
    )
    category_id: int = Field(
        foreign_key="csv_category.id",
        sa_column_kwargs={"info": {"site_props": {"target_service": "csv_category"}}},
    )
    internal_note: str = Field(
        default="",
        sa_column_kwargs={"info": {"site_props": {"exportable": False}}},
    )


class CsvItemTag(SQLModel, table=True):
    __tablename__ = "csv_item_tag"
    __onesite__ = {
        "is_link_table": True,
        "m2m": {"directions": [{"from": "csv_item", "to": "csv_tag"}]},
    }

    csv_item_id: int = Field(
        foreign_key="csv_item.id",
        primary_key=True,
        sa_column_kwargs={"info": {"site_props": {"target_service": "csv_item"}}},
    )
    csv_tag_id: int = Field(
        foreign_key="csv_tag.id",
        primary_key=True,
        sa_column_kwargs={"info": {"site_props": {"target_service": "csv_tag"}}},
    )


class CustomCsvDocument(SQLModel, table=True):
    __tablename__ = "custom_csv_document"
    __onesite__ = {
        "importable": {"custom": True},
        "exportable": {"custom": True},
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str


class ExportPermissionItem(SQLModel, table=True):
    __tablename__ = "export_permission_item"
    __onesite__ = {
        "exportable": {"fields": ["code", "admin_note"]},
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str
    admin_note: str = Field(
        default="",
        sa_column_kwargs={
            "info": {
                "site_props": {
                    "permissions": {
                        "user": "",
                        "admin": "r",
                        "developer": "r",
                    }
                }
            }
        },
    )


def _models():
    definitions = []
    for cls, module in (
        (CsvCategory, "csv_category"),
        (CsvTag, "csv_tag"),
        (CsvItem, "csv_item"),
        (CsvItemTag, "csv_item_tag"),
        (CustomCsvDocument, "custom_csv_document"),
        (ExportPermissionItem, "export_permission_item"),
    ):
        result = get_model_fields(cls, module)
        definitions.append(_build_model_dict(cls.__name__, module, module, result))
    phase_resolve_relationships(definitions)
    return {model.name: model for model in definitions}


def _service_template():
    directory = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    return Environment(loader=FileSystemLoader(directory)).get_template("service.py.j2")


def _template(name: str):
    directory = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    return Environment(loader=FileSystemLoader(directory)).get_template(name)


def test_config_resolves_selected_fields_fk_lookup_and_explicit_m2m():
    item = _models()["CsvItem"]

    assert [column["name"] for column in item.export_fields] == [
        "sku", "name", "category_id"
    ]
    assert next(column for column in item.export_fields if column["kind"] == "fk")[
        "lookup_field"
    ] == "title"
    assert [relation["column_name"] for relation in item.export_m2m] == ["tags"]
    assert item.export_m2m[0]["lookup_field"] == "title"
    assert [relation["column_name"] for relation in item.import_m2m] == ["tags"]
    assert item.export_fields[0]["header_labels"] == {"en": "SKU", "zh": "商品编码"}
    assert item.export_fields[1]["header_labels"] == {
        "en": "Product name",
        "zh": "商品名称",
    }
    assert item.export_fields[2]["header_labels"] == {"en": "Category", "zh": "分类"}


def test_generated_service_uses_semicolon_m2m_and_rejects_missing_relations():
    model = _models()["CsvItem"]
    rendered = _service_template().render(model=model)

    ast.parse(rendered)
    assert 'row.append(";".join(csvtag_ids_values.get(item.id, [])))' in rendered
    assert '.split(";")' in rendered
    assert "Foreign key '{value}' not found for field 'category_id'" in rendered
    assert "M2M values not found for 'tags'" in rendered
    assert "await self.update(session, existing.id, obj_in)" in rendered
    assert "await self.create(session, obj_in)" in rendered
    assert '"en": "SKU"' in rendered
    assert '.get(language, "sku")' in rendered
    assert 'language = "zh" if str(language).lower().startswith("zh") else "en"' in rendered

    api = _template("api.py.j2").render(model=model)
    handler = _template("export_handler.py.j2").render(model=model)
    frontend_service = _template("frontend_service.ts.j2").render(model=model)
    frontend_page = _template("frontend_page_list.tsx.j2").render(model=model)
    ast.parse(api)
    ast.parse(handler)
    assert 'language: str = Query("en", description="CSV header language")' in api
    assert '"language": language,' in api
    assert 'language = payload.get("language", "en")' in handler
    assert 'language=language,' in handler
    assert 'exportCsvItems = async (language: string, filters?: Record<string, any>)' in frontend_service
    assert '`${API_URL}/export`, filters' in frontend_service
    assert 'params: { language }' in frontend_service
    assert 'for key, value in (filters or {}).items()' in rendered
    assert '"name",' in rendered
    assert 'session, page=page, size=batch_size, **export_filters' in rendered
    assert 'await exportCsvItems(' in frontend_page
    assert 'useCsvItemStore.getState().filters' in frontend_page


def test_exportable_reverse_foreign_key_is_resolved_and_rendered_as_one_column():
    category = _models()["CsvCategory"]

    assert len(category.export_reverse_fks) == 1
    relation = category.export_reverse_fks[0]
    assert relation["source_model"] == "CsvItem"
    assert relation["source_fk_field"] == "category_id"
    assert relation["lookup_field"] == "name"
    assert relation["column_name"] == "csv_items"
    assert relation["header_labels"] == {"en": "Products", "zh": "商品"}

    rendered = _service_template().render(model=category)
    ast.parse(rendered)
    assert 'getattr(reverse_csv_item_category_id_values_model, "name")' in rendered
    assert 'row.append(";".join(reverse_csv_item_category_id_values.get(item.id, [])))' in rendered
    assert '.get(language, "csv_items")' in rendered


def test_unconfigured_m2m_is_not_exported_by_legacy_boolean_mode():
    item = _models()["CsvCategory"]
    assert item.export_m2m == []
    assert item.import_m2m == []


def test_custom_import_export_generates_preserved_background_hooks(tmp_path):
    assert _process_introspected_class(
        CustomCsvDocument, "CustomCsvDocument", "custom_csv_document"
    ) is not None
    model = _models()["CustomCsvDocument"]

    assert model.custom_importable is True
    assert model.custom_exportable is True

    service = _service_template().render(model=model)
    api = _template("api.py.j2").render(model=model)
    handler = _template("export_handler.py.j2").render(model=model)
    custom_io = _template("custom_io.py.j2").render(model=model)
    frontend_service = _template("frontend_service.ts.j2").render(model=model)
    frontend_page = _template("frontend_page_list.tsx.j2").render(model=model)

    ast.parse(service)
    ast.parse(api)
    ast.parse(handler)
    assert "async def import_from_csv" not in service
    assert "async def export_to_csv" not in service
    assert 'task_queue.publish(\n        "import.custom_csv_document"' in api
    assert "from app.custom_io.custom_csv_document import export_custom_csv_document" in handler
    assert "from app.custom_io.custom_csv_document import import_custom_csv_document" in handler
    assert "async def import_custom_csv_document(file: Path)" in custom_io
    assert "async def export_custom_csv_document(filters: dict[str, Any]) -> Path" in custom_io
    assert "Promise<ImportTask>" in frontend_service
    assert "Import started, you will be notified when complete" in frontend_page

    (tmp_path / "app").mkdir()
    backend_path = tmp_path / "generated" / "backend"
    _generate_custom_io_handler(model, tmp_path, backend_path)
    source_hook = tmp_path / "app" / "custom_io" / "custom_csv_document.py"
    generated_hook = backend_path / "app" / "custom_io" / "custom_csv_document.py"
    assert source_hook.exists()
    assert generated_hook.read_text(encoding="utf-8") == source_hook.read_text(encoding="utf-8")

    source_hook.write_text("# developer implementation\n", encoding="utf-8")
    _generate_custom_io_handler(model, tmp_path, backend_path)
    assert generated_hook.read_text(encoding="utf-8") == "# developer implementation\n"


def test_standard_export_carries_role_and_filters_scalar_columns_by_read_permission():
    model = _models()["ExportPermissionItem"]

    service = _service_template().render(model=model)
    api = _template("api.py.j2").render(model=model)
    handler = _template("export_handler.py.j2").render(model=model)

    ast.parse(service)
    ast.parse(api)
    ast.parse(handler)
    assert '"current_role": current_role' in api
    assert 'payload.get("current_role", "developer")' in handler
    assert "current_role=current_role" in handler
    assert 'current_role: str = "developer"' in service
    assert "export_column_permissions" in service
    assert '"admin_note": {"admin": "r", "developer": "r", "user": ""}' in service
    assert 'if "r" in permissions.get(role, "")' in service
    assert 'if "admin_note" in readable_export_columns' in service


def test_embedded_import_export_preserves_scope_and_passes_fixed_fields():
    model = _models()["CsvItem"]
    page = _template("frontend_page_list.tsx.j2").render(model=model)
    embedded_actions = page.split('data-page-region="embedded-toolbar"', 1)[1].split("} : (<>", 1)[0]
    assert "onClick={handleImportClick}" in embedded_actions
    assert "onClick={handleExport}" in embedded_actions
    assert "hasPermission('c') && hasPermission('u')" in embedded_actions
    assert "hasPermission('r')" in embedded_actions
    assert "...scopeFilters }" in page
    assert "queueImportCsvItems(importingFile, fixedFields)" in page
    api = _template("api.py.j2").render(model=model)
    assert '"category_id":' in api.split("allowed_fixed_fields =", 1)[1]
    assert 'fixed_fields=import_fixed_fields' in api
    handler = _template("export_handler.py.j2").render(model=model)
    assert 'fixed_fields=fixed_fields' in handler
    ast.parse(api)
    ast.parse(handler)
