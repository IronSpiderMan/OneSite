import asyncio
import importlib
import json
import sqlite3
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from sqlalchemy.exc import OperationalError

from onesite.codegen.assets import sync_backend_assets, sync_frontend_assets


def _site_config():
    return {
        "project_name": "Error handling test",
        "secret_key": "test",
        "access_token_expire_minutes": 30,
        "database_url": "sqlite:///./test.db",
        "allowed_origins": [],
        "upload_dir": "uploads",
        "desktop": {
            "api_url": "http://127.0.0.1:8000/api/v1",
            "version": "0.1.0",
            "identifier": "com.onesite.error-handling-test",
            "width": 1280,
            "height": 800,
        },
    }


def test_backend_error_handler_is_synced_and_registered(tmp_path):
    (tmp_path / "app").mkdir()
    backend = tmp_path / "generated" / "backend"

    sync_backend_assets(tmp_path, backend, _site_config())

    handler = backend / "app" / "core" / "error_handlers.py"
    main = backend / "app" / "main.py"
    assert handler.exists()
    assert '"code": "DATABASE_SCHEMA_MISMATCH"' in handler.read_text(encoding="utf-8")
    assert "register_error_handlers(app)" in main.read_text(encoding="utf-8")


def test_application_resources_are_synced_and_used_by_lifespan(tmp_path):
    source = tmp_path / "app"
    source.mkdir()
    resources = source / "resources.py"
    resources.write_text(
        "from fastapi import FastAPI\n\n"
        "async def init_resources(app: FastAPI) -> None:\n"
        "    app.state.ready = True\n\n"
        "async def destroy_resources(app: FastAPI) -> None:\n"
        "    app.state.ready = False\n",
        encoding="utf-8",
    )
    backend = tmp_path / "generated" / "backend"

    sync_backend_assets(tmp_path, backend, _site_config())

    generated_resources = backend / "app" / "resources.py"
    assert generated_resources.read_text(encoding="utf-8") == resources.read_text(
        encoding="utf-8"
    )
    main = (backend / "app" / "main.py").read_text(encoding="utf-8")
    assert "from app.resources import destroy_resources, init_resources" in main
    assert "await init_resources(app)" in main
    assert "await destroy_resources(app)" in main
    assert main.index("await init_resources(app)") < main.index("yield")
    assert main.index("yield") < main.index("await destroy_resources(app)")


def test_frontend_distinguishes_server_failure_from_offline(tmp_path):
    (tmp_path / "app").mkdir()

    sync_frontend_assets(tmp_path, _site_config())

    request_file = (
        tmp_path / "generated" / "frontend" / "src" / "utils" / "request.ts"
    ).read_text(encoding="utf-8")
    assert "error.response.status >= 500" in request_file
    assert "toast.error(typeof detail === 'string'" in request_file
    assert "suppressErrorToast?: boolean" in request_file
    assert "error.response.status >= 500 && !suppressErrorToast" in request_file
    assert "navigator.onLine === false" in request_file
    assert "redirectTo('/error/500')" not in request_file


def test_sqlite_missing_column_returns_schema_mismatch_response(
    tmp_path, monkeypatch
):
    template_backend = (
        Path(__file__).parents[1] / "src" / "onesite" / "templates" / "backend"
    )
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.syspath_prepend(str(template_backend))
    previous_app_modules = {
        name: module
        for name, module in sys.modules.items()
        if name == "app" or name.startswith("app.")
    }
    for name in previous_app_modules:
        sys.modules.pop(name)
    try:
        error_handlers = importlib.import_module("app.core.error_handlers")

        error = OperationalError(
            "SELECT event.level FROM event",
            {},
            sqlite3.OperationalError("no such column: event.level"),
        )
        assert error_handlers._is_schema_mismatch(error)

        app = FastAPI()
        error_handlers.register_error_handlers(app)
        handler = app.exception_handlers[OperationalError]
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "scheme": "http",
                "path": "/api/v1/events",
                "root_path": "",
                "query_string": b"",
                "headers": [],
                "client": ("test", 123),
                "server": ("testserver", 80),
            }
        )
        response = asyncio.run(handler(request, error))

        assert response.status_code == 503
        body = json.loads(response.body)
        assert body["code"] == "DATABASE_SCHEMA_MISMATCH"
        assert "event.level" not in body["detail"]
    finally:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                sys.modules.pop(name)
        sys.modules.update(previous_app_modules)
