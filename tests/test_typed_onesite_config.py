from types import SimpleNamespace

from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from onesite.config import (
    DetailUIConfig,
    EditMode,
    FormUIConfig,
    ImportExportConfig,
    HiddenTask,
    ModelAction,
    ModelUIConfig,
    OneSiteConfig,
    ReportDimensionInput,
    ReportInputs,
    ReportLimits,
    ReportMeasureInput,
    ReportsConfig,
    TimeSeriesTableConfig,
    TreeLeafConfig,
    TreeViewConfig,
    SiteConfig,
    TaskCenterConfig,
    normalize_onesite_config,
)
from onesite.codegen.introspect import _build_json_model_schema, get_model_fields
from onesite.codegen.phases.introspect_models import _introspect_module


class TypedProduct(SQLModel, table=True):
    __tablename__ = "typed_product"
    __onesite__ = OneSiteConfig(
        permissions={"user": "r", "admin": "crud", "developer": "crud"},
        visible=["admin", "developer"],
        edit_mode="drawer",
        actions={"toggle_enabled": ModelAction(toggle="enabled", permissions="da")},
        import_key="sku",
        importable=ImportExportConfig(fields=["sku", "name"]),
    )

    id: int | None = Field(default=None, primary_key=True)
    sku: str
    name: str
    enabled: bool = True


class TypedJsonConfig(BaseModel):
    __onesite__ = OneSiteConfig(
        ui=ModelUIConfig(
            detail=DetailUIConfig(layout=[["client_id", "enabled"]])
        )
    )
    __i18n__ = {"zh": {"client_id": "客户端 ID", "enabled": "启用"}}

    client_id: str = ""
    enabled: bool = True


def test_typed_ui_config_supports_an_independent_form_layout():
    normalized = normalize_onesite_config(
        OneSiteConfig(
            ui=ModelUIConfig(
                detail=DetailUIConfig(layout=[["name"]]),
                form=FormUIConfig(layout=[["name", "owner_id"]]),
            )
        )
    )

    assert normalized["ui"]["detail"]["layout"] == [["name"]]
    assert normalized["ui"]["form"]["layout"] == [["name", "owner_id"]]


def test_typed_onesite_config_normalizes_only_explicit_fields():
    assert normalize_onesite_config(OneSiteConfig()) == {}
    assert normalize_onesite_config(OneSiteConfig(edit_mode="drawer")) == {
        "edit_mode": "drawer"
    }
    assert normalize_onesite_config(OneSiteConfig(edit_mode="inplace_edit")) == {
        "edit_mode": "inplace_edit"
    }
    assert normalize_onesite_config(
        OneSiteConfig(edit_mode=EditMode.PAGE_EDIT)
    ) == {"edit_mode": "page"}


def test_edit_mode_enum_exposes_all_supported_editor_presentations():
    assert EditMode.FORM_EDIT.value == "modal"
    assert EditMode.PAGE_EDIT.value == "page"
    assert EditMode.INPLACE_EDIT.value == "inplace_edit"
    assert EditMode.DRAWER_EDIT.value == "drawer"


def test_typed_tree_view_config_normalizes_leaf_model_options():
    config = OneSiteConfig(
        tree_view=TreeViewConfig(
            leaf=TreeLeafConfig(
                model="AssetDocument",
                parent_field="folder_id",
                label_field="name",
                page_size=20,
            )
        )
    )

    assert normalize_onesite_config(config)["tree_view"] == {
        "leaf": {
            "model": "AssetDocument",
            "parent_field": "folder_id",
            "label_field": "name",
            "page_size": 20,
        }
    }


def test_typed_report_config_normalizes_to_the_dictionary_pipeline():
    config = OneSiteConfig(
        reports=ReportsConfig(
            categories=["cartesian", "scatter"],
            inputs=ReportInputs(
                x={"created_at": ReportDimensionInput(bins=["none", "day"])},
                y={"amount": ReportMeasureInput(aggregations=["raw", "sum"])},
                cls=["status"],
                count=["$rows"],
            ),
            filters=["created_at", "status"],
            limits=ReportLimits(max_rows=2000),
        )
    )

    reports = normalize_onesite_config(config)["reports"]
    assert reports["categories"] == ["cartesian", "scatter"]
    assert reports["inputs"]["x"]["created_at"]["bins"] == ["none", "day"]
    assert reports["inputs"]["y"]["amount"]["aggregations"] == ["raw", "sum"]
    assert reports["limits"]["max_rows"] == 2000
    assert normalize_onesite_config(
        OneSiteConfig(
            time_series_table=TimeSeriesTableConfig(
                entity_field="device_id", time_field="created_at"
            )
        )
    ) == {
        "time_series_table": {
            "entity_field": "device_id",
            "time_field": "created_at",
        }
    }


def test_typed_task_center_hidden_config_serializes_kind_and_name():
    config = SiteConfig(
        task_center=TaskCenterConfig(
            hidden=[HiddenTask(kind="tool", name="internal_cleanup")]
        )
    )
    assert config.model_dump(mode="json")["task_center"] == {
        "hidden": [{"kind": "tool", "name": "internal_cleanup"}]
    }


def test_typed_onesite_config_uses_existing_introspection_pipeline():
    result = get_model_fields(TypedProduct, "typed_product")

    assert result.edit_mode == "drawer"
    assert result.role_visible == {"user": False, "admin": True, "developer": True}
    assert result.model_site_props["importable"] == {
        "fields": ["sku", "name"]
    }
    assert result.model_site_props["actions"]["toggle_enabled"]["data"] == {
        "enabled": "!{{value}}"
    }


def test_typed_onesite_config_supports_json_submodel_layout():
    schema = _build_json_model_schema(TypedJsonConfig)
    assert schema["layout"][0]["columns"] == 2
    assert [item["field"] for item in schema["layout"][0]["items"]] == [
        "client_id",
        "enabled",
    ]
    assert schema["fields"][0]["labelKey"] == "json_models.typed_json_config.fields.client_id"
    assert schema["fields"][0]["translations"] == {"zh": "客户端 ID"}


def test_typed_frontend_only_config_marks_non_table_sqlmodel_for_introspection():
    class FrontendSettings(SQLModel):
        __onesite__ = OneSiteConfig(frontend_only=True)
        value: str = ""

    module = SimpleNamespace(FrontendSettings=FrontendSettings)
    models = _introspect_module(module, "frontend_settings")
    assert models is not None
    assert [model.name for model in models] == ["FrontendSettings"]
