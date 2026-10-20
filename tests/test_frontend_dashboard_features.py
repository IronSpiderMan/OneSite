import json
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader
from typer.testing import CliRunner

from onesite.codegen.config import SiteConfigError
from onesite.codegen.config import validate_custom_features_config
from onesite.codegen.frontend_features import load_frontend_features, sync_frontend_features
from onesite.codegen.i18n import generate_locale_files
from onesite.main import app


TEMPLATES = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"


def _feature_config(*, frontend_only: bool = False) -> dict:
    return {
        "name": "ops_dashboard", "frontend_only": frontend_only, "backend_only": False,
        "dependencies": {"dayjs": "^1.11.0"}, "dev_dependencies": {}, "locales": {},
        "pages": [
            {"id": "workspace", "path": "/operations", "layout": "app",
             "access": ["user", "admin", "developer"],
             "menu": {"title": {"zh": "运营工作台", "en": "Operations"},
                      "icon": "Activity", "visible": None}},
            {"id": "status", "path": "/public/status", "layout": "public",
             "access": ["user", "admin", "developer"], "menu": None},
        ],
        "overrides": [{"target": "builtin.dashboard"}],
        "dashboard_widgets": [{
            "id": "pulse", "title": {"zh": "运行脉搏", "en": "Operations Pulse"},
            "span": {"md": 12, "xl": 8}, "order": 100,
            "access": ["admin", "developer"], "frame": True,
        }],
    }


def test_site_config_feature_scaffolds_and_compiles_frontend(tmp_path):
    features = load_frontend_features(tmp_path, [_feature_config()])
    source = tmp_path / "app/frontend/features/ops_dashboard"
    assert (source / "pages/Workspace.tsx").exists()
    assert (source / "pages/Status.tsx").exists()
    assert (source / "pages/DashboardOverride.tsx").exists()
    assert (source / "components/PulseWidget.tsx").exists()
    assert (source / "stores/useOpsDashboardStore.ts").exists()
    service = (source / "services/ops_dashboard.ts").read_text(encoding="utf-8")
    assert "request.get<CustomFeatureData>('/custom/ops-dashboard')" in service
    feature = features[0]
    assert feature["routes"][0]["id"] == "ops_dashboard.workspace"
    assert feature["overrides"][0]["target"] == "builtin.dashboard"
    assert feature["dashboard_widgets"][0]["id"] == "ops_dashboard.pulse"
    assert feature["locales"]["zh"]["widgets"]["pulse"]["title"] == "运行脉搏"


def test_frontend_only_service_never_calls_missing_backend(tmp_path):
    load_frontend_features(tmp_path, [_feature_config(frontend_only=True)])
    service = (tmp_path / "app/frontend/features/ops_dashboard/services/ops_dashboard.ts").read_text(encoding="utf-8")
    assert "return { items: [], total: 0 }" in service
    assert "request" not in service


def test_scaffold_never_overwrites_developer_source(tmp_path):
    config = _feature_config()
    load_frontend_features(tmp_path, [config])
    page = tmp_path / "app/frontend/features/ops_dashboard/pages/Workspace.tsx"
    page.write_text("export default function Mine() { return null }\n", encoding="utf-8")
    load_frontend_features(tmp_path, [config])
    assert page.read_text(encoding="utf-8") == "export default function Mine() { return null }\n"


def test_frontend_feature_syncs_source_and_merges_dependencies(tmp_path):
    features = load_frontend_features(tmp_path, [_feature_config()])
    shared = tmp_path / "app/frontend/shared"
    shared.mkdir(parents=True)
    (shared / "format.ts").write_text("export const format = String;\n", encoding="utf-8")
    frontend = tmp_path / "generated/frontend"
    frontend.mkdir(parents=True)
    (frontend / "package.json").write_text(
        json.dumps({"dependencies": {"react": "^18.2.0"}, "devDependencies": {}}), encoding="utf-8"
    )
    sync_frontend_features(tmp_path, frontend, features)
    copied = frontend / "src/custom/features/ops_dashboard"
    assert (copied / "pages/Workspace.tsx").exists()
    assert (frontend / "src/custom/shared/format.ts").exists()
    package = json.loads((frontend / "package.json").read_text(encoding="utf-8"))
    assert package["dependencies"]["dayjs"] == "^1.11.0"


def test_frontend_feature_locales_are_namespaced(tmp_path):
    features = load_frontend_features(tmp_path, [_feature_config()])
    locale_dir = tmp_path / "locales"
    generate_locale_files([], locale_dir, frontend_features=features)
    zh = json.loads((locale_dir / "zh.json").read_text(encoding="utf-8"))
    assert zh["features"]["ops_dashboard"]["widgets"]["pulse"]["title"] == "运行脉搏"


def test_route_and_widget_registries_use_scaffolded_components(tmp_path):
    feature = load_frontend_features(tmp_path, [_feature_config()])[0]
    routes = [{**route, "feature_name": feature["name"]} for route in feature["routes"]]
    overrides = [{**item, "feature_name": feature["name"]} for item in feature["overrides"]]
    route_source = Environment(loader=FileSystemLoader(TEMPLATES)).get_template(
        "frontend_feature_routes.tsx.j2"
    ).render(routes=routes, overrides=overrides)
    assert "./custom/features/ops_dashboard/pages/Workspace" in route_source
    assert '"builtin.dashboard": {' in route_source
    widget = {**feature["dashboard_widgets"][0], "feature_name": feature["name"]}
    widget_source = Environment(loader=FileSystemLoader(TEMPLATES)).get_template(
        "frontend_dashboard_widgets.tsx.j2"
    ).render(widgets=[widget])
    assert "./custom/features/ops_dashboard/components/PulseWidget" in widget_source


def test_legacy_feature_manifest_is_rejected(tmp_path):
    legacy = tmp_path / "app/frontend/features/old/feature.py"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("feature = object()\n", encoding="utf-8")
    with pytest.raises(SiteConfigError, match="no longer supported"):
        load_frontend_features(tmp_path, [])


def test_component_path_cannot_escape_feature_source(tmp_path):
    config = _feature_config()
    config["pages"][0]["component"] = "../../Outside.tsx"
    with pytest.raises(SiteConfigError, match="must stay inside"):
        load_frontend_features(tmp_path, [config])
    assert not (tmp_path / "app/frontend/Outside.tsx").exists()


def test_custom_feature_modes_are_mutually_exclusive():
    config = {
        "custom_features": [
            {"name": "invalid", "frontend_only": True, "backend_only": True}
        ]
    }
    with pytest.raises(SiteConfigError, match="cannot both be true"):
        validate_custom_features_config(config)


def test_backend_only_rejects_frontend_declarations():
    config = {
        "custom_features": [
            {
                "name": "invalid",
                "backend_only": True,
                "pages": [{"id": "page", "path": "/page"}],
            }
        ]
    }
    with pytest.raises(SiteConfigError, match="backend_only"):
        validate_custom_features_config(config)


def test_site_sync_scaffolds_and_registers_configured_feature(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    created = runner.invoke(app, ["create", "FeatureApp"])
    assert created.exit_code == 0, created.output
    project = tmp_path / "FeatureApp"
    config_path = project / "site_config.py"
    source = config_path.read_text(encoding="utf-8")
    source = source.replace(
        "from onesite.config import DesktopConfig, SiteConfig, env, sqlite_url",
        "from onesite.config import (CustomFeature, CustomFeatureMenu, CustomOverride, CustomPage, DesktopConfig, SiteConfig, env, sqlite_url)",
    ).replace(
        "    desktop=DesktopConfig(",
        "    custom_features=[CustomFeature(\n"
        "        name='operations',\n"
        "        pages=[CustomPage(id='workspace', path='/operations', menu=CustomFeatureMenu(title={'zh': '运营', 'en': 'Operations'}))],\n"
        "        overrides=[CustomOverride(target='builtin.dashboard')],\n"
        "    )],\n"
        "    desktop=DesktopConfig(",
    )
    config_path.write_text(source, encoding="utf-8")
    monkeypatch.chdir(project)
    synced = runner.invoke(app, ["sync"])
    assert synced.exit_code == 0, synced.output
    assert (project / "app/frontend/features/operations/pages/Workspace.tsx").exists()
    assert (project / "app/backend/api/operations.py").exists()
    registry = (project / "generated/frontend/src/GeneratedFeatureRoutes.tsx").read_text(encoding="utf-8")
    api = (project / "generated/backend/app/api/api.py").read_text(encoding="utf-8")
    assert 'id: "operations.workspace"' in registry
    assert '"builtin.dashboard": {' in registry
    assert "from app.api.endpoints.custom import operations as custom_api_0" in api
