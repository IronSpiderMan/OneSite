"""OPC UA plugin generation, profile validation and live address-space browsing."""

import sys

import pytest

from onesite.codegen.assets import _sync_integration_requirements
from onesite.codegen.phases.introspect_models import phase_introspect
from onesite.codegen.phases.opcua import generate_opcua
from onesite.codegen.phases.plugin_models import phase_generate_plugin_models
from onesite.codegen.phases.relationships import phase_resolve_relationships
from onesite.codegen.phases.sync_models import phase_sync_models
from onesite.codegen.render import create_template_environment
from onesite.codegen.router import update_api_router


def generate(tmp_path):
    backend = tmp_path / "generated/backend"
    phase_sync_models(tmp_path, backend)
    phase_generate_plugin_models({"plugins": ["opcua"]}, tmp_path, backend)
    models = phase_introspect(backend)
    phase_resolve_relationships(models)
    generate_opcua(models, {"plugins": ["opcua"]}, tmp_path, backend)
    # The runtime only needs upload settings for these isolated tests.
    (backend / "app/core/config.py").write_text(
        f"from types import SimpleNamespace\nsettings = SimpleNamespace(UPLOAD_DIR={str(tmp_path / 'uploads')!r}, PRIVATE_UPLOAD_DIR={str(tmp_path / 'private')!r})\n"
    )
    return backend, {model["name"]: model for model in models}


def test_models_detail_browser_and_plugin_lifecycle(tmp_path):
    backend, models = generate(tmp_path)
    server = models["OpcuaServer"]
    assert {field["name"] for field in server["fields"] if field["is_enum"]} == {
        "auth_type",
        "security_policy",
        "security_mode",
    }
    node = models["OpcuaNode"]
    assert next(f for f in node["fields"] if f["name"] == "collection_mode")["is_enum"]
    assert not node["standalone"] and not models["OpcuaAc"]["standalone"]
    assert not any(node["role_visible"].values())
    assert {
        rel["source_model"] for rel in server["reverse_foreign_keys"] if rel["editor"] == "embedded"
    } == {"OpcuaNode", "OpcuaAc"}
    assert next(f for f in server["fields"] if f["name"] == "key_path")["private_upload"]
    for theme in ("normal", "arco", "industrial", "neuron"):
        detail = (
            create_template_environment(theme)
            .get_template("frontend_page_detail.tsx.j2")
            .render(model=server)
        )
        assert "<OpcuaBrowsePanel" in detail
        assert "onAdded={() => setBrowseVersion" in detail
        assert "-${browseVersion}`" in detail
        assert "canAddNodes=" in detail and "canAddAcs=" in detail
    update_api_router([], backend / "app/api/api.py", opcua_enabled=True)
    assert 'prefix="/opcua"' in (backend / "app/api/api.py").read_text()
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("fastapi\n")
    _sync_integration_requirements(requirements, {"plugins": ["opcua"]})
    _sync_integration_requirements(requirements, {"plugins": ["opcua"]})
    assert requirements.read_text().count("asyncua") == 1
    generate_opcua(list(models.values()), {}, tmp_path, backend)
    assert not (backend / "app/core/opcua.py").exists()
    assert not (tmp_path / "generated/frontend/src/components/opcua/BrowsePanel.tsx").exists()
    assert not server["opcua_browse"]
    update_api_router([], backend / "app/api/api.py")
    assert "opcua_browse" not in (backend / "app/api/api.py").read_text()
    phase_sync_models(tmp_path, backend)
    phase_generate_plugin_models({}, tmp_path, backend)
    assert not (backend / "app/models/opcua_server.py").exists()


def test_interval_defaults_reach_create_forms(tmp_path):
    _, models = generate(tmp_path)
    expected = {
        "OpcuaServer": {
            "request_timeout_seconds": 10,
            "reconnect_interval_seconds": 5,
            "publishing_interval_ms": 1000,
        },
        "OpcuaNode": {
            "sampling_interval_ms": 1000,
            "polling_interval_seconds": 1,
        },
    }
    for model_name, defaults in expected.items():
        model = models[model_name]
        fields = {field["name"]: field for field in model["fields"]}
        for name, value in defaults.items():
            assert fields[name]["default"] == value
        for theme in ("normal", "arco", "industrial", "neuron"):
            env = create_template_environment(theme)
            for template in ("frontend_page_create.tsx.j2", "frontend_page_list.tsx.j2"):
                page = env.get_template(template).render(model=model)
                assert "defaultValues:" in page
                for name, value in defaults.items():
                    assert f"{name}: {value}," in page
                if template == "frontend_page_list.tsx.j2" and not model["page_edit"]:
                    # Opening another create form resets previous edits to defaults.
                    assert "setEditingId(null);" in page
                    assert "reset();" in page


def test_project_can_override_plugin_model(tmp_path):
    source = tmp_path / "app/models/opcua_node.py"
    source.parent.mkdir(parents=True)
    source.write_text("PROJECT_OVERRIDE = True\n")
    backend = tmp_path / "backend"
    phase_sync_models(tmp_path, backend)
    phase_generate_plugin_models({"plugins": ["opcua"]}, tmp_path, backend)
    assert (backend / "app/models/opcua_node.py").read_text() == source.read_text()
    assert (backend / "app/models/opcua_ac.py").exists()


@pytest.mark.parametrize(
    "scenario",
    [
        "profile_validation_and_secrets",
        "database_uniqueness_and_cascade",
        "live_browse_with_custom_condition_and_namespace_uri",
        "browse_api_permissions_validation_and_error_redaction",
        "live_secure_browse_uses_saved_certificates",
    ],
)
def test_runtime_scenario(tmp_path, scenario):
    import os
    import subprocess
    from pathlib import Path

    root = Path(__file__).parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(root / "src") + os.pathsep + os.environ.get("PYTHONPATH", ""),
    }
    result = subprocess.run(
        [sys.executable, str(root / "tests/support/opcua_scenario.py"), scenario, str(tmp_path)],
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
