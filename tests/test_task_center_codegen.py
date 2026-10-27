"""Unified Task Center generation, retention, and navigation coverage."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest
from jinja2 import Environment, FileSystemLoader
from typer.testing import CliRunner

from onesite.codegen.config import (
    SiteConfigError,
    validate_navigation_config,
    validate_task_center_config,
)
from onesite.codegen.i18n import generate_locale_files
from onesite.codegen.phases.generate import _build_navigation
from onesite.codegen.router import update_api_router
from onesite.main import app


TEMPLATE_DIR = (
    Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
)


def test_import_export_runtime_and_api_templates_compile():
    environment = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    for template_name in (
        "import_export_runtime.py.j2",
        "task_center_api.py.j2",
        "background_execution_cleanup.py.j2",
    ):
        rendered = environment.get_template(template_name).render()
        compile(rendered, template_name, "exec")

    # ``owner_id`` is the stable CRUD scope argument; it must not be replaced
    # with an arbitrary configured owner field name in queued export filters.
    api_template = (TEMPLATE_DIR / "api.py.j2").read_text(encoding="utf-8")
    handler_template = (TEMPLATE_DIR / "export_handler.py.j2").read_text(
        encoding="utf-8"
    )
    service_template = (TEMPLATE_DIR / "service.py.j2").read_text(encoding="utf-8")
    runtime_template = (TEMPLATE_DIR / "import_export_runtime.py.j2").read_text(
        encoding="utf-8"
    )
    task_api_template = (TEMPLATE_DIR / "task_center_api.py.j2").read_text(
        encoding="utf-8"
    )
    assert 'effective_filters["owner_id"] = current_user.id' in api_template
    assert 'scoped_owner_id=filters.get("owner_id")' in handler_template
    assert '{% if model.owner_field %}"owner_id",' in service_template
    assert '"created_at": _iso_datetime(execution.created_at)' in runtime_template
    assert 'TASK_KINDS = ("import", "export", "tool", "scheduled_task")' in task_api_template
    assert "_execution_dict(item, include_details=False)" in task_api_template

    cleanup_template = (
        TEMPLATE_DIR / "background_execution_cleanup.py.j2"
    ).read_text(encoding="utf-8")
    assert "RETENTION_PERIOD = timedelta(days=1)" in cleanup_template
    assert 'TERMINAL_STATUSES = ("succeeded", "failed")' in cleanup_template


def test_import_export_builtin_navigation_and_locales(tmp_path):
    validate_navigation_config(
        {"navigation": [{"type": "builtin", "key": "task-center"}]}
    )
    menu = _build_navigation(
        None,
        [],
        reports_enabled=False,
        reports_role_visible={"user": False, "admin": False, "developer": False},
        import_export_enabled=True,
        import_export_role_visible={"user": True, "admin": True, "developer": True},
    )
    task_item = next(item for item in menu if item["key"] == "/task-center")
    assert task_item["icon"] == "ArrowRightLeft"
    assert task_item["visible"]["user"] is True

    generate_locale_files([], tmp_path)
    en = json.loads((tmp_path / "en.json").read_text(encoding="utf-8"))
    zh = json.loads((tmp_path / "zh.json").read_text(encoding="utf-8"))
    assert en["menu"]["task_center"] == "Task Center"
    assert zh["menu"]["task_center"] == "任务中心"
    assert zh["task_center"]["kinds"]["tool"] == "工具"
    assert zh["task_center"]["kinds"]["scheduled_task"] == "定时任务"
    assert zh["task_center"]["statuses"]["running"] == "执行中"


def test_router_registers_task_center_api(tmp_path):
    api_path = tmp_path / "api.py"
    update_api_router([], api_path, import_export_enabled=True)
    source = api_path.read_text(encoding="utf-8")
    assert "from app.api.endpoints import task_center" in source
    assert 'prefix="/task-center"' in source


def test_task_center_hidden_config_is_validated():
    config = {
        "task_center": {
            "hidden": [
                {"kind": "tool", "name": "internal_cleanup"},
                {"kind": "export", "name": "audit_log"},
            ]
        }
    }
    validate_task_center_config(config)
    assert config["task_center"]["hidden"][0] == {
        "kind": "tool",
        "name": "internal_cleanup",
    }


@pytest.mark.parametrize(
    "hidden",
    [
        "tool:internal_cleanup",
        [{"kind": "unknown", "name": "internal_cleanup"}],
        [{"kind": "tool", "name": "bad-name"}],
        [
            {"kind": "tool", "name": "internal_cleanup"},
            {"kind": "tool", "name": "internal_cleanup"},
        ],
    ],
)
def test_invalid_task_center_hidden_config_is_rejected(hidden):
    with pytest.raises(SiteConfigError):
        validate_task_center_config({"task_center": {"hidden": hidden}})


def test_io_only_site_sync_generates_trackable_task_feature(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    created = runner.invoke(app, ["create", "ImportExportApp"])
    assert created.exit_code == 0, created.output

    project = tmp_path / "ImportExportApp"
    model_file = project / "app" / "models" / "inventory_item.py"
    model_file.write_text(
        "from typing import Optional\n"
        "from sqlmodel import Field, SQLModel\n\n"
        "class InventoryItem(SQLModel, table=True):\n"
        "    __onesite__ = {\n"
        "        'importable': True,\n"
        "        'exportable': True,\n"
        "        'import_key': 'sku',\n"
        "    }\n"
        "    id: Optional[int] = Field(default=None, primary_key=True)\n"
        "    sku: str = Field(unique=True, index=True)\n"
        "    name: str\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(project)
    synced = runner.invoke(app, ["sync"])
    assert synced.exit_code == 0, synced.output

    backend = project / "generated" / "backend" / "app"
    frontend = project / "generated" / "frontend" / "src"

    assert (backend / "core" / "background_execution.py").exists()
    assert (backend / "core" / "import_export_runtime.py").exists()
    assert (backend / "api" / "endpoints" / "task_center.py").exists()
    assert (backend / "handlers" / "export_inventory_item.py").exists()
    assert (frontend / "pages" / "TaskCenter.tsx").exists()
    assert (frontend / "services" / "task-center.ts").exists()

    db_source = (backend / "core" / "db.py").read_text(encoding="utf-8")
    main_source = (backend / "main.py").read_text(encoding="utf-8")
    router_source = (backend / "api" / "api.py").read_text(encoding="utf-8")
    endpoint_source = (
        backend / "api" / "endpoints" / "inventory_item.py"
    ).read_text(encoding="utf-8")
    handler_source = (
        backend / "handlers" / "export_inventory_item.py"
    ).read_text(encoding="utf-8")
    service_source = (
        backend / "services" / "inventory_item.py"
    ).read_text(encoding="utf-8")
    routes_source = (frontend / "Routes.tsx").read_text(encoding="utf-8")
    menu_source = (frontend / "Menu.tsx").read_text(encoding="utf-8")
    list_page_source = (
        frontend / "pages" / "inventory_item" / "index.tsx"
    ).read_text(encoding="utf-8")

    assert "import app.core.background_execution" in db_source
    assert "reconcile_interrupted_import_export_executions" in main_source
    assert 'prefix="/task-center"' in router_source
    assert "BackgroundExecution(" in endpoint_source
    assert "background: bool = Query(False" in endpoint_source
    assert "if not background:" in endpoint_source
    assert 'task_queue.handler("import.inventory_item")' in handler_source
    assert "progress_callback=context.set_progress" in handler_source
    assert 'f"importing_records:{idx}:{total_rows}"' in service_source
    assert 'f"exporting_records:{processed_items}:{total_items}"' in service_source
    assert "TaskCenterPage" in routes_source
    assert 'key: "/task-center"' in menu_source
    assert "queueImportInventoryItems" in list_page_source
    assert "View progress" in list_page_source

    for python_file in backend.rglob("*.py"):
        compile(python_file.read_text(encoding="utf-8"), str(python_file), "exec")


def test_import_codegen_enforces_write_permissions_owner_scope_and_field_roles(
    tmp_path, monkeypatch
):
    """CSV import must not become a model/field/owner permission bypass."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    created = runner.invoke(app, ["create", "ImportPermissionApp"])
    assert created.exit_code == 0, created.output

    project = tmp_path / "ImportPermissionApp"
    models = project / "app" / "models"
    (models / "import_permission_probe.py").write_text(
        "from typing import Optional\n"
        "from sqlmodel import Field, SQLModel\n\n"
        "class ImportPermissionProbe(SQLModel, table=True):\n"
        "    __tablename__ = 'import_permission_probe'\n"
        "    __onesite__ = {\n"
        "        'permissions': {\n"
        "            'user': 'rc',\n"
        "            'admin': 'crud',\n"
        "            'developer': 'crud',\n"
        "        },\n"
        "        'importable': True,\n"
        "        'import_key': 'code',\n"
        "    }\n"
        "    id: Optional[int] = Field(default=None, primary_key=True)\n"
        "    code: str = Field(unique=True, index=True)\n"
        "    name: str\n",
        encoding="utf-8",
    )
    (models / "owned_import_item.py").write_text(
        "from typing import Optional\n"
        "from sqlmodel import Field, SQLModel\n\n"
        "class OwnedImportItem(SQLModel, table=True):\n"
        "    __tablename__ = 'owned_import_item'\n"
        "    __onesite__ = {\n"
        "        'permissions': {\n"
        "            'user': 'cru',\n"
        "            'admin': 'crud',\n"
        "            'developer': 'crud',\n"
        "        },\n"
        "        'owner_field': 'owner_id',\n"
        "        'importable': {\n"
        "            'fields': ['sku', 'name', 'protected_note', 'owner_id'],\n"
        "        },\n"
        "        'exportable': {\n"
        "            'fields': ['sku', 'name', 'protected_note'],\n"
        "        },\n"
        "        'import_key': 'sku',\n"
        "    }\n"
        "    id: Optional[int] = Field(default=None, primary_key=True)\n"
        "    sku: str = Field(\n"
        "        unique=True,\n"
        "        index=True,\n"
        "        sa_column_kwargs={'info': {'site_props': {'permissions': {\n"
        "            'user': 'cr', 'admin': 'cru', 'developer': 'cru'\n"
        "        }}}},\n"
        "    )\n"
        "    name: str\n"
        "    protected_note: str = Field(\n"
        "        default='',\n"
        "        sa_column_kwargs={'info': {'site_props': {'permissions': {\n"
        "            'user': '', 'admin': 'r', 'developer': 'cru'\n"
        "        }}}},\n"
        "    )\n"
        "    owner_id: int = Field(foreign_key='user.id')\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(project)
    synced = runner.invoke(app, ["sync"])
    assert synced.exit_code == 0, synced.output

    generated = project / "generated" / "backend" / "app"
    probe_api = (
        generated / "api" / "endpoints" / "import_permission_probe.py"
    ).read_text(encoding="utf-8")
    owner_api = (
        generated / "api" / "endpoints" / "owned_import_item.py"
    ).read_text(encoding="utf-8")
    owner_handler = (
        generated / "handlers" / "export_owned_import_item.py"
    ).read_text(encoding="utf-8")
    owner_service = (
        generated / "services" / "owned_import_item.py"
    ).read_text(encoding="utf-8")

    # A role with read+create but no update must still be rejected because a
    # CSV upsert can perform either operation.
    assert "def _check_import_permission_probe_import_permissions" in probe_api
    assert '"user": "rc"' in probe_api
    assert 'if "c" not in permissions or "u" not in permissions' in probe_api
    assert "status_code=403" in probe_api
    assert "_check_import_permission_probe_import_permissions(current_user)" in probe_api

    # The request-derived role and owner scope must survive both the legacy
    # synchronous path and the queued path.
    assert "current_role=current_role" in owner_api
    assert "scoped_owner_id=scoped_owner_id" in owner_api
    assert '"current_role": current_role' in owner_api
    assert '"scoped_owner_id": scoped_owner_id' in owner_api
    assert "Export requires read permission" in owner_api
    assert 'payload.get("current_role", "developer")' in owner_handler
    assert 'payload.get("scoped_owner_id")' in owner_handler
    assert "current_role=current_role" in owner_handler
    assert "scoped_owner_id=scoped_owner_id" in owner_handler
    assert "AsyncSession(engine, expire_on_commit=False)" in owner_handler

    # The service is the final trust boundary: it must select columns by the
    # current role, require c/u according to the actual upsert branch, force
    # non-admin ownership, and reject a matching key owned by another user.
    assert 'current_role: str = "developer"' in owner_service
    assert "scoped_owner_id: Any = None" in owner_service
    assert "import_column_permissions" in owner_service
    assert (
        '"protected_note": {"admin": "r", "developer": "cru", "user": ""}'
        in owner_service
    )
    assert 'required_permission = "u" if is_update else "c"' in owner_service
    assert "required_permission not in" in owner_service
    assert 'and "sku" == import_key' in owner_service
    assert 'and "r" in permissions' in owner_service
    assert "A scoped import always ignores an untrusted owner value" in owner_service
    assert 'obj_data["owner_id"] = scoped_owner_id' in owner_service
    assert 'getattr(existing, "owner_id", None) != scoped_owner_id' in owner_service
    assert "readable_export_columns" in owner_service
    assert 'if "r" in permissions.get(role, "")' in owner_service

    for source in (probe_api, owner_api, owner_handler, owner_service):
        compile(source, "generated import permission source", "exec")

    # Exercise the generated trust boundary, not just its emitted shape.  The
    # subprocess isolates the generated ``app`` package and SQLModel metadata
    # from OneSite's own test process.
    backend = project / "generated" / "backend"
    database = tmp_path / "import-permission-runtime.db"
    runtime_check = textwrap.dedent(
        """
        import asyncio
        import csv
        import io
        import json
        from types import SimpleNamespace

        from fastapi import HTTPException, UploadFile
        from sqlmodel import select
        from sqlmodel.ext.asyncio.session import AsyncSession

        from app.api.endpoints.import_permission_probe import (
            _check_import_permission_probe_import_permissions,
        )
        from app.core.background_execution import BackgroundExecution
        from app.core.db import engine, init_db
        from app.core.import_export_runtime import ImportExportContext, execution_to_dict
        from app.models.owned_import_item import OwnedImportItem
        from app.services.owned_import_item import service


        def assert_endpoint_permissions():
            try:
                _check_import_permission_probe_import_permissions(
                    SimpleNamespace(role="user")
                )
            except HTTPException as exc:
                assert exc.status_code == 403
            else:
                raise AssertionError("read+create role bypassed update requirement")

            _check_import_permission_probe_import_permissions(
                SimpleNamespace(role="admin")
            )


        def csv_upload(contents: str) -> UploadFile:
            return UploadFile(
                filename="items.csv",
                file=io.BytesIO(contents.encode("utf-8")),
            )


        async def progress_context(task_id: str, kind: str) -> ImportExportContext:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                session.add(
                    BackgroundExecution(
                        id=task_id,
                        kind=kind,
                        name="owned_import_item",
                        requested_by=101,
                    )
                )
                await session.commit()
            return ImportExportContext(task_id)


        async def run():
            assert_endpoint_permissions()
            await init_db()

            async with AsyncSession(engine, expire_on_commit=False) as session:
                session.add(
                    OwnedImportItem(
                        sku="foreign-sku",
                        name="Other user's row",
                        protected_note="unchanged",
                        owner_id=202,
                    )
                )
                session.add(
                    OwnedImportItem(
                        sku="own-sku",
                        name="Own old name",
                        protected_note="unchanged",
                        owner_id=101,
                    )
                )
                await session.commit()

            async with AsyncSession(engine, expire_on_commit=False) as session:
                cross_owner = await service.import_from_csv(
                    session,
                    task_id="cross-owner",
                    user_id=101,
                    file=csv_upload("sku,name\\nforeign-sku,overwritten\\n"),
                    current_role="user",
                    scoped_owner_id=101,
                )
                assert cross_owner["success"] == 0, cross_owner
                assert cross_owner["failed"] == 1, cross_owner

            async with AsyncSession(engine, expire_on_commit=False) as session:
                scoped = await service.import_from_csv(
                    session, task_id="embedded-scope", user_id=101,
                    file=csv_upload("sku,name,owner_id\\nforeign-sku,Wrong,101\\nscoped-new,Scoped,invalid\\n"),
                    current_role="developer", fixed_fields={"owner_id": 101},
                )
                assert scoped["failed"] == 1, scoped
                assert scoped["created"] == 1, scoped
                created = (await session.exec(select(OwnedImportItem).where(
                    OwnedImportItem.sku == "scoped-new"
                ))).one()
                assert created.owner_id == 101

            # The key is needed to locate an update but is not itself writable
            # for this role.  It must be consumed for lookup and then omitted
            # from the update payload without rejecting the row.
            async with AsyncSession(engine, expire_on_commit=False) as session:
                immutable_key = await service.import_from_csv(
                    session,
                    task_id="immutable-key",
                    user_id=101,
                    file=csv_upload("sku,name\\nown-sku,Own new name\\n"),
                    current_role="user",
                    scoped_owner_id=101,
                )
                assert immutable_key["success"] == 1, immutable_key
                assert immutable_key["updated"] == 1, immutable_key

            async with AsyncSession(engine, expire_on_commit=False) as session:
                forbidden_field = await service.import_from_csv(
                    session,
                    task_id="field-permission",
                    user_id=101,
                    file=csv_upload(
                        "sku,name,protected_note\\nnew-secret,Name,forbidden\\n"
                    ),
                    current_role="user",
                    scoped_owner_id=101,
                )
                assert forbidden_field["success"] == 0, forbidden_field
                assert forbidden_field["failed"] == 1, forbidden_field

            async with AsyncSession(engine, expire_on_commit=False) as session:
                allowed_progress = await progress_context("allowed", "import")
                allowed = await service.import_from_csv(
                    session,
                    task_id="allowed",
                    user_id=101,
                    file=csv_upload(
                        "sku,name,protected_note,owner_id\\n"
                        "new-ok,Allowed row,,attacker-supplied-owner\\n"
                    ),
                    current_role="user",
                    scoped_owner_id=101,
                    progress_callback=allowed_progress.set_progress,
                )
                assert allowed["success"] == 1, allowed
                assert allowed["created"] == 1, allowed

            async with AsyncSession(engine, expire_on_commit=False) as session:
                rows = (await session.exec(select(OwnedImportItem))).all()
                by_sku = {row.sku: row for row in rows}
                assert by_sku["foreign-sku"].name == "Other user's row"
                assert by_sku["own-sku"].name == "Own new name"
                assert "new-secret" not in by_sku
                assert by_sku["new-ok"].owner_id == 101

            async with AsyncSession(engine, expire_on_commit=False) as session:
                user_export_progress = await progress_context("user-export", "export")
                developer_export_progress = await progress_context(
                    "developer-export", "export"
                )
                user_export = await service.export_to_csv(
                    session,
                    task_id="user-export",
                    user_id=101,
                    filters={"owner_id": 101},
                    language="en",
                    current_role="user",
                    progress_callback=user_export_progress.set_progress,
                )
                developer_export = await service.export_to_csv(
                    session,
                    task_id="developer-export",
                    user_id=101,
                    filters={"owner_id": 101},
                    language="en",
                    current_role="developer",
                    progress_callback=developer_export_progress.set_progress,
                )

            async with AsyncSession(engine, expire_on_commit=False) as session:
                allowed_execution = await session.get(BackgroundExecution, "allowed")
                assert allowed_execution.progress == 98
                assert (
                    await session.get(BackgroundExecution, "user-export")
                ).progress == 98
                # WebSocket send_json uses the standard JSON encoder.
                json.dumps(execution_to_dict(allowed_execution))

            with open(user_export, encoding="utf-8-sig", newline="") as source:
                user_rows = list(csv.reader(source))
            with open(developer_export, encoding="utf-8-sig", newline="") as source:
                developer_rows = list(csv.reader(source))

            assert len(user_rows[0]) == 2, user_rows[0]
            assert all(len(row) == 2 for row in user_rows[1:])
            assert "unchanged" not in {cell for row in user_rows for cell in row}
            assert len(developer_rows[0]) == 3, developer_rows[0]
            assert all(len(row) == 3 for row in developer_rows[1:])
            assert "unchanged" in {cell for row in developer_rows for cell in row}

        async def checked_run():
            try:
                await run()
            finally:
                await engine.dispose()


        asyncio.run(checked_run())
        """
    )
    environment = os.environ.copy()
    environment["DATABASE_URI"] = f"sqlite+aiosqlite:///{database}"
    generated_runtime_modules = (
        "aiosqlite",
        "greenlet",
        "jose",
        "multipart",
        "pydantic_settings",
    )
    missing_runtime_modules = [
        module
        for module in generated_runtime_modules
        if importlib.util.find_spec(module) is None
    ]
    if missing_runtime_modules:
        pytest.skip(
            "generated backend runtime dependencies are not installed: "
            + ", ".join(missing_runtime_modules)
        )
    checked = subprocess.run(
        [sys.executable, "-c", runtime_check],
        cwd=backend,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert checked.returncode == 0, checked.stdout + checked.stderr
