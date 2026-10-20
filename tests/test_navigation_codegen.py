"""Coverage for the declarative, two-level navigation tree."""

import json
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

from onesite.codegen.config import SiteConfigError, validate_navigation_config
from onesite.codegen.i18n import generate_locale_files
from onesite.codegen.phases.generate import _build_navigation


def _model(module_name: str) -> dict:
    return {
        "module_name": module_name,
        "is_singleton": False,
        "icon": "TableProperties",
        "role_visible": {"user": True, "admin": True, "developer": True},
        "owner_field": None,
    }


def test_navigation_groups_models_without_model_level_navigation_config():
    navigation_config = [
        {"type": "model", "model": "record"},
        {
            "type": "group",
            "key": "data-sources",
            "label": {"zh": "数据源", "en": "Data Sources"},
            "icon": "Database",
            "default_open": True,
            "children": [
                {"type": "model", "model": "opcua"},
                {"type": "model", "model": "opcua_node"},
            ],
        },
    ]
    validate_navigation_config({"navigation": navigation_config})
    menu = _build_navigation(
        navigation_config,
        [
            _model("record"),
            _model("opcua"),
            _model("opcua_node"),
            _model("unconfigured_record"),
        ],
        reports_enabled=False,
        reports_role_visible={"user": False, "admin": False, "developer": False},
    )

    assert menu[0]["key"] == "/records"
    assert menu[1]["type"] == "group"
    assert menu[1]["key"] == "group:data-sources"
    assert [child["key"] for child in menu[1]["children"]] == [
        "/opcuas",
        "/opcua_nodes",
    ]
    assert menu[2]["key"] == "/unconfigured_records"

    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    rendered = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_menu.tsx.j2"
    ).render(navigation=menu, used_icons=["Database", "TableProperties"])
    assert "type: 'group'" in rendered
    assert 'key: "group:data-sources"' in rendered
    assert "function findMenuItem" in rendered
    assert "function findMenuPath" in rendered
    assert "function matchesMenuItemPath" in rendered
    assert "normalizedPathname.startsWith(`${normalizedMenuPath}/`)" in rendered
    assert "return [node, ...childPath]" in rendered


def test_navigation_rejects_nested_groups_and_duplicate_models():
    with pytest.raises(SiteConfigError, match="nested groups"):
        validate_navigation_config(
            {
                "navigation": [
                    {
                        "type": "group",
                        "key": "parent",
                        "label": {"zh": "父级", "en": "Parent"},
                        "children": [
                            {
                                "type": "group",
                                "key": "child",
                                "label": {"zh": "子级", "en": "Child"},
                                "children": [{"type": "model", "model": "record"}],
                            }
                        ],
                    }
                ]
            }
        )

    with pytest.raises(SiteConfigError, match="duplicate model 'record'"):
        validate_navigation_config(
            {
                "navigation": [
                    {"type": "model", "model": "record"},
                    {"type": "model", "model": "record"},
                ]
            }
        )

    validate_navigation_config(
        {"navigation": [{"type": "builtin", "key": "external-resources"}]}
    )


def test_navigation_group_labels_are_written_to_both_locales(tmp_path):
    generate_locale_files(
        [],
        tmp_path,
        [
            {
                "type": "group",
                "key": "group:data-sources",
                "translations": {"zh": "数据源", "en": "Data Sources"},
            }
        ],
    )

    assert json.loads((tmp_path / "en.json").read_text(encoding="utf-8"))["menu"]["groups"] == {
        "data-sources": "Data Sources"
    }
    assert json.loads((tmp_path / "zh.json").read_text(encoding="utf-8"))["menu"]["groups"] == {
        "data-sources": "数据源"
    }


def test_active_group_child_does_not_highlight_group_trigger():
    layout = (
        Path(__file__).parents[1]
        / "src"
        / "onesite"
        / "templates"
        / "frontend"
        / "src"
        / "components"
        / "Layout.tsx"
    ).read_text(encoding="utf-8")

    assert "item.defaultOpen || containsActiveItem" in layout
    assert "containsActiveItem ? NAV_ACTIVE[theme] : NAV_INACTIVE[theme]" not in layout
    assert "NAV_INACTIVE[theme]\n                      )}" in layout


def test_navigation_can_reference_frontend_feature_route():
    navigation_config = [
        {
            "type": "group",
            "key": "operations",
            "label": {"zh": "运营", "en": "Operations"},
            "children": [{"type": "route", "route": "ops.workspace"}],
        }
    ]
    custom_routes = [
        {
            "id": "ops.workspace",
            "path": "/operations",
            "menu": {
                "icon": "Activity",
                "label": "features.ops.routes.workspace.menu",
                "visible": {"user": True, "admin": True, "developer": True},
            },
        }
    ]

    validate_navigation_config({"navigation": navigation_config})
    menu = _build_navigation(
        navigation_config,
        [],
        custom_routes,
        reports_enabled=False,
        reports_role_visible={"user": False, "admin": False, "developer": False},
    )

    assert menu[0]["children"][0]["key"] == "/operations"
    assert menu[0]["children"][0]["label"] == "features.ops.routes.workspace.menu"


def test_navigation_accepts_legacy_source_name_without_duplicating_the_menu():
    config = [{"type": "group", "key": "devices", "label": {"en": "Devices"},
               "children": [{"type": "model", "model": "dgroup"}]}]
    models = [{**_model("d_group"), "source_module": "dgroup"}, _model("device")]
    menu = _build_navigation(config, models, reports_enabled=False, reports_role_visible={})
    assert menu[0]["children"][0]["key"] == "/d_groups"
    assert [node["key"] for node in menu] == ["group:devices", "/devices"]
    assert config[0]["children"][0]["model"] == "dgroup"


def test_navigation_rejects_ambiguous_source_alias():
    models = [{**_model(key), "source_module": "entities"} for key in ("first", "second")]
    with pytest.raises(ValueError, match="ambiguous source module.*entities.*first, second"):
        _build_navigation([{"type": "model", "model": "entities"}], models,
                          reports_enabled=False, reports_role_visible={})


def test_navigation_rejects_duplicate_canonical_and_legacy_references():
    models = [{**_model("d_group"), "source_module": "dgroup"}]
    with pytest.raises(ValueError, match="duplicates model 'd_group'"):
        _build_navigation([{"type": "model", "model": key} for key in ("dgroup", "d_group")],
                          models, reports_enabled=False, reports_role_visible={})
