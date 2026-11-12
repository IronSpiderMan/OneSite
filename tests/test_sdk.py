"""Exercise the SDK command and the standalone wheel it produces."""

from importlib import import_module
import json
from urllib.parse import parse_qs
from zipfile import ZipFile

import httpx
import pytest
from typer.testing import CliRunner

from onesite.main import app


def test_builds_custom_crud_wheel_with_client_managed_token(tmp_path, monkeypatch):
    backend = tmp_path / "generated" / "backend" / "app"
    backend.mkdir(parents=True)
    (backend / "main.py").write_text(
        """
from fastapi import Depends, FastAPI
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

app = FastAPI(title="Widget Hub")

@app.on_event("startup")
def startup():
    raise RuntimeError("SDK export must not run application startup")

class Widget(BaseModel):
    name: str

class AgentMessage(BaseModel):
    text: str

auth = OAuth2PasswordBearer(tokenUrl="/api/v1/login/access-token")

@app.post("/api/v1/login/access-token")
def login():
    return {}

@app.get("/api/v1/widgets/", tags=["widgets"], openapi_extra={"x-onesite-crud": "list"})
def list_widgets(page: int = 1, tags: str | None = None, token: str = Depends(auth)) -> list[Widget]:
    return []

@app.put("/api/v1/widgets/{id}", tags=["widgets"], openapi_extra={"x-onesite-crud": "update"})
def update_widget(id: str, widget: Widget, token: str = Depends(auth)) -> Widget:
    return widget

@app.post("/api/v1/widgets/bulk_delete", tags=["widgets"])
def bulk_delete():
    return {}

@app.get("/api/v1/agents", tags=["agents"])
def agents() -> list[AgentMessage]:
    return []
""",
        encoding="utf-8",
    )
    (tmp_path / "sdk.json").write_text(
        json.dumps({"name": "widget-sdk-test", "version": "2.1.0", "output": "wheels"}),
        encoding="utf-8",
    )
    monkeypatch.setattr("onesite.main.get_cwd_safely", lambda: tmp_path)
    result = CliRunner().invoke(app, ["sdk", "build"])
    assert result.exit_code == 0, result.output
    wheel, = (tmp_path / "wheels").glob("widget_sdk_test-2.1.0-*.whl")
    with ZipFile(wheel) as archive:
        assert archive.testzip() is None
        assert "widget_sdk_test/py.typed" in archive.namelist()
        assert "AgentMessage" not in archive.read("widget_sdk_test/models.py").decode()

    monkeypatch.syspath_prepend(str(wheel))
    sdk = import_module("widget_sdk_test")
    assert sdk.OPERATIONS == {
        ("GET", "/api/v1/widgets/"): ("widgets", "list"),
        ("PUT", "/api/v1/widgets/{id}"): ("widgets", "update"),
    }
    assert sdk.models.Widget.__required_keys__ == {"name"}

    calls = []

    def respond(request):
        calls.append(request)
        if request.url.path.endswith("/login/access-token"):
            assert request.headers.get("authorization") is None
            assert parse_qs(request.content.decode()) == {
                "username": ["sdk@example.com"],
                "password": ["test-password"],
                "grant_type": ["password"],
            }
            return httpx.Response(200, json={"access_token": "test-token"})
        if request.method == "PUT":
            assert request.url.raw_path == b"/proxy/api/v1/widgets/a%2Fb"
            assert json.loads(request.content) == {"name": "pump"}
            return httpx.Response(401, json={"detail": "Could not validate credentials"})
        assert request.url.params == httpx.QueryParams({"page": 2})
        return httpx.Response(200, json=[{"name": "pump"}])

    with sdk.Client("https://hub.example.com/proxy", transport=httpx.MockTransport(respond)) as client:
        client.login(email="sdk@example.com", password="test-password")
        assert client.widgets.list(page=2) == [{"name": "pump"}]
        assert not hasattr(client, "agents")
        assert not hasattr(client.widgets, "bulk_delete")
        with pytest.raises(sdk.AuthenticationExpired) as error:
            client.widgets.update(id="a/b", body={"name": "pump"})
        assert error.value.status_code == 401
        assert client.widgets.list(page=2) == [{"name": "pump"}]

    assert [request.headers.get("authorization") for request in calls] == [
        None, "Bearer test-token", "Bearer test-token", None,
    ]


def test_explains_how_to_regenerate_schema_without_sdk_markers(tmp_path, monkeypatch):
    schema = tmp_path / "openapi.json"
    schema.write_text(
        json.dumps({"paths": {"/api/v1/agents": {"get": {"tags": ["agents"]}}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr("onesite.main.get_cwd_safely", lambda: tmp_path)

    result = CliRunner().invoke(app, ["sdk", "build", "--openapi", str(schema)])

    assert result.exit_code == 1
    assert "No custom model CRUD routes found. Run site sync" in result.output
