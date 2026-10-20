import pytest
from sqlmodel import Field, SQLModel
from typer.testing import CliRunner

from onesite.config import OneSiteConfig, normalize_onesite_config
from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import phase_introspect
from onesite.codegen.phases.relationships import phase_resolve_relationships
from onesite.codegen.phases.sync_models import phase_sync_models
from onesite.codegen.phases.generate import _generate_regular_model
from onesite.main import app


class TrackedItem(SQLModel, table=True):
    __tablename__ = "tracked_item_test"
    __onesite__ = {"track": ["crud", "bulk_delete"]}

    id: int | None = Field(default=None, primary_key=True)
    name: str


def test_track_config_normalizes_crud_and_extended_operations():
    result = get_model_fields(TrackedItem, "tracked_item")

    assert result.model_site_props["tracked_operations"] == [
        "create", "read", "update", "delete", "bulk_delete"
    ]
    assert normalize_onesite_config(OneSiteConfig(track="ru"))["track"] == "ru"


def test_track_config_rejects_invalid_or_unavailable_operations():
    class InvalidTrack(SQLModel, table=True):
        __tablename__ = "invalid_track_test"
        __onesite__ = {"track": "x"}
        id: int | None = Field(default=None, primary_key=True)

    class InvalidImportTrack(SQLModel, table=True):
        __tablename__ = "invalid_import_track_test"
        __onesite__ = {"track": ["import"]}
        id: int | None = Field(default=None, primary_key=True)

    with pytest.raises(ValueError, match="only c, r, u, d"):
        get_model_fields(InvalidTrack, "invalid_track")
    with pytest.raises(ValueError, match="importable is disabled"):
        get_model_fields(InvalidImportTrack, "invalid_import_track")


def test_tracking_generates_owner_scoped_read_only_log_model_and_api(tmp_path):
    source_models = tmp_path / "app" / "models"
    source_models.mkdir(parents=True)
    (source_models / "tracked_widget.py").write_text(
        "from typing import Optional\n"
        "from sqlmodel import Field, SQLModel\n\n"
        "class TrackedWidget(SQLModel, table=True):\n"
        "    __onesite__ = {'track': ['crud', 'bulk_delete']}\n"
        "    id: Optional[int] = Field(default=None, primary_key=True)\n"
        "    name: str\n",
        encoding="utf-8",
    )
    backend = tmp_path / "generated" / "backend"
    phase_sync_models(tmp_path, backend)

    models = phase_introspect(backend)
    phase_resolve_relationships(models)
    by_name = {model["name"]: model for model in models}

    operation_log = by_name["OperationLog"]
    assert operation_log["owner_field"] == "user_id"
    assert [fk["name"] for fk in operation_log["foreign_keys"]] == ["user_id"]
    assert operation_log["foreign_keys"][0]["target_model"] == "User"
    assert not operation_log["foreign_keys"][0]["reverse_display"]
    assert operation_log["read_only"] is True
    assert operation_log["role_permissions"] == {
        "user": "r", "admin": "r", "developer": "r"
    }
    assert operation_log["tracked_operations"] == []

    _generate_regular_model(operation_log, tmp_path, backend)
    api = (backend / "app" / "api" / "endpoints" / "operation_log.py").read_text()
    compile(api, "generated_operation_log_api.py", "exec")
    assert '@router.get("/",' in api
    assert '@router.get("/{id}"' in api
    assert "@router.post" not in api
    assert "@router.put" not in api
    assert "@router.delete" not in api
    assert "owner_id = current_user.id" in api


def test_generated_tracked_api_has_request_metadata(tmp_path):
    result = get_model_fields(TrackedItem, "tracked_item")
    from onesite.codegen.phases.introspect_models import _build_model_dict

    model = _build_model_dict(
        "TrackedItem", "tracked_item", "tracked_item", result,
        table_name="tracked_item_test",
    )
    model.update({
        "min_role_for_read": "USER",
        "min_role_for_create": "USER",
        "min_role_for_update": "USER",
        "min_role_for_delete": "USER",
        "reverse_foreign_keys": [],
        "inline_relations": [],
        "dict_key_reference_meta": [],
        "reverse_definition_bindings": [],
        "definition_binding_meta": None,
        "m2m_fields": [],
        "reverse_m2m": [],
        "has_function_actions": False,
        "has_dynamic_action_states": False,
        "has_read_resolvers": False,
        "is_timescaledb": False,
        "dashboard_metrics": [],
        "reports": None,
        "network_device": None,
        "uses_composite_identity": False,
    })
    _generate_regular_model(model, tmp_path, tmp_path / "backend")
    api = (tmp_path / "backend" / "app" / "api" / "endpoints" / "tracked_item.py").read_text()
    compile(api, "generated_tracked_item_api.py", "exec")
    for operation in ("create", "read", "update", "delete", "bulk_delete"):
        assert f'operation="{operation}"' in api


def test_site_sync_generates_complete_tracking_feature(tmp_path, monkeypatch):
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    created = runner.invoke(app, ["create", "TrackingApp"])
    assert created.exit_code == 0, created.output

    project = tmp_path / "TrackingApp"
    (project / "app" / "models" / "tracked_asset.py").write_text(
        "from typing import Optional\n"
        "from sqlmodel import Field, SQLModel\n\n"
        "class TrackedAsset(SQLModel, table=True):\n"
        "    __onesite__ = {\n"
        "        'track': ['crud', 'bulk_delete', 'import', 'export'],\n"
        "        'importable': True,\n"
        "        'exportable': True,\n"
        "        'import_key': 'name',\n"
        "    }\n"
        "    id: Optional[int] = Field(default=None, primary_key=True)\n"
        "    name: str = Field(unique=True)\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(project)
    synced = runner.invoke(app, ["sync"])
    assert synced.exit_code == 0, synced.output

    backend = project / "generated" / "backend" / "app"
    frontend = project / "generated" / "frontend" / "src"
    assert (backend / "models" / "operation_log.py").exists()
    assert (backend / "core" / "operation_tracking.py").exists()

    main_source = (backend / "main.py").read_text(encoding="utf-8")
    tracked_api = (
        backend / "api" / "endpoints" / "tracked_asset.py"
    ).read_text(encoding="utf-8")
    log_api = (
        backend / "api" / "endpoints" / "operation_log.py"
    ).read_text(encoding="utf-8")
    log_model = (
        backend / "models" / "operation_log.py"
    ).read_text(encoding="utf-8")
    log_schema = (
        backend / "schemas" / "operation_log.py"
    ).read_text(encoding="utf-8")
    log_crud = (
        backend / "cruds" / "operation_log.py"
    ).read_text(encoding="utf-8")
    db_source = (backend / "core" / "db.py").read_text(encoding="utf-8")
    io_handler = (
        backend / "handlers" / "export_tracked_asset.py"
    ).read_text(encoding="utf-8")
    menu = (frontend / "Menu.tsx").read_text(encoding="utf-8")
    en_locale = (frontend / "locales" / "en.json").read_text(encoding="utf-8")

    assert "OperationTrackingMiddleware" in main_source
    assert "tracked_operation" in tracked_api
    assert 'operation="import"' in tracked_api
    assert 'operation="export"' in tracked_api
    assert 'operation="import"' in io_handler
    assert 'operation="export"' in io_handler
    assert "@router.post" not in log_api
    assert 'foreign_key="user.id"' in log_model
    assert "user_id_label: Optional[str] = None" in log_schema
    assert 'getattr(obj, "email", None)' in log_crud
    assert 'CONSTRAINT "fk_operation_log_user_id_user"' in db_source
    assert 'key: "/operation_logs"' in menu
    assert '"plural": "Operation Logs"' in en_locale
    assert '"my_name": "My Operation Logs"' in en_locale
    for python_file in backend.rglob("*.py"):
        compile(python_file.read_text(encoding="utf-8"), str(python_file), "exec")
