"""Regression coverage for generated external-resource configuration."""

import json
from pathlib import Path
import pytest
from jinja2 import Environment, FileSystemLoader
from typer.testing import CliRunner

from onesite.codegen.assets import _validate_external_resource_provider
from onesite.codegen.phases.generate import _normalize_external_resource
from onesite.codegen.config import SiteConfigError
from onesite.main import app


TEMPLATE_DIR = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"


def test_external_resource_declaration_maps_one_model_to_provider_resource():
    model = {
        "name": "Camera",
        "module_name": "camera",
        "fields": [{"name": "id"}, {"name": "external_key"}],
    }

    assert _normalize_external_resource(
        model,
        {"provider": "edgeflow", "resource": "cameras", "identity": "external_key"},
    ) == {
        "provider": "edgeflow",
        "resource": "cameras",
        "identity_field": "external_key",
    }
    assert _normalize_external_resource(
        model,
        {"provider": "edgeflow", "resource_type": "legacy-camera"},
    )["resource"] == "legacy-camera"
def test_external_resource_config_is_project_specific_and_provider_aware():
    environment = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    resources_json = json.dumps([
        {"provider": "edgeflow", "resource": "device"},
        {"provider": "edgeflow", "resource": "gateway"},
    ])
    source = environment.get_template("external_resource_config.py.j2").render(
        resources_json=resources_json
    )
    namespace: dict[str, object] = {}
    exec(compile(source, "external_resource_config.py", "exec"), namespace)

    get_resource_config = namespace["get_resource_config"]
    assert get_resource_config("edgeflow", "device") == {
        "provider": "edgeflow",
        "resource": "device",
    }
    assert get_resource_config("edgeflow", "gateway")["resource"] == "gateway"
    with pytest.raises(ValueError, match="Unknown external resource"):
        get_resource_config("edgeflow", "missing")


def test_external_resource_runtime_imports_project_configuration():
    environment = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    source = environment.get_template("external_resources.py.j2").render()

    assert "resources_json" not in source
    assert "RESOURCE_CONFIGS" in source
    assert "get_model_resource_config" in source
    assert "class ExternalProviderState" in source
    assert "class ExternalResourceTask" not in source
    assert "class ExternalResourceBinding" not in source
    assert "sync_external_resource_change" in source
    assert "reconcile_provider" in source
    assert "AsyncIOScheduler" in source
    assert "asyncio.create_task" in source
    assert "while True" not in source
    compile(source, "external_resources.py", "exec")


def test_old_reconciliation_provider_gets_a_migration_error(tmp_path):
    provider = tmp_path / "legacy.py"
    provider.write_text(
        "class Provider:\n"
        "    async def build_desired(self, session, resource_type, entity, binding):\n"
        "        return {}\n",
        encoding="utf-8",
    )

    with pytest.raises(SiteConfigError, match="create/update/delete/reconcile"):
        _validate_external_resource_provider(provider)


def test_project_sync_generates_multi_resource_provider_cud_delivery(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("onesite.main.get_cwd_safely", lambda: tmp_path)
    runner = CliRunner()
    created = runner.invoke(app, ["create", "ExternalApp"])
    assert created.exit_code == 0, created.output

    project = tmp_path / "ExternalApp"
    config_path = project / "site_config.py"
    config_source = config_path.read_text(encoding="utf-8")
    config_source = config_source.replace(
        "from onesite.config import DesktopConfig, SiteConfig, env, sqlite_url",
        "from onesite.config import (DesktopConfig, ExternalResourceProviderConfig, SiteConfig, env, sqlite_url)",
    ).replace(
        "    desktop=DesktopConfig(",
        "    providers={'edgeflow': ExternalResourceProviderConfig(module='edgeflow')},\n"
        "    desktop=DesktopConfig(",
    )
    config_path.write_text(config_source, encoding="utf-8")
    (project / "app" / "models" / "camera.py").write_text(
        "from typing import Optional\n"
        "from sqlmodel import Field, SQLModel\n\n"
        "class Camera(SQLModel, table=True):\n"
        "    __onesite__ = {'external_resource': {'provider': 'edgeflow', 'resource': 'cameras'}}\n"
        "    id: Optional[int] = Field(default=None, primary_key=True)\n"
        "    name: str\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(project)
    synced = runner.invoke(app, ["sync"])
    assert synced.exit_code == 0, synced.output

    generated = project / "generated" / "backend" / "app"
    runtime = (generated / "core" / "external_resources.py").read_text(encoding="utf-8")
    service = (generated / "services" / "camera.py").read_text(encoding="utf-8")
    provider = (project / "app" / "providers" / "edgeflow.py").read_text(encoding="utf-8")
    assert "class ExternalProviderState" in runtime
    assert "ExternalResourceBinding" not in runtime
    assert "ExternalResourceTask" not in runtime
    assert "desired_generation" in runtime
    assert "AsyncIOScheduler" in runtime
    assert "enqueue_external_resource_change" not in service
    assert "async def create(self, resource:" in provider
    assert "async def update(" in provider
    assert "async def delete(self, resource:" in provider
    assert "async def reconcile(" in provider
    assert (generated / "api" / "endpoints" / "external_resources.py").exists()
    assert (project / "generated" / "frontend" / "src" / "pages" / "ExternalResources.tsx").exists()
    assert "/external-resources" in (generated / "api" / "api.py").read_text(encoding="utf-8")
    assert "/external-resources" in (
        project / "generated" / "frontend" / "src" / "Routes.tsx"
    ).read_text(encoding="utf-8")
