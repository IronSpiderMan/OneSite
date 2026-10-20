"""Coverage for the compact enable/disable action declaration."""

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel

from onesite.codegen.i18n import generate_locale_files
from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict


class FeatureFlag(SQLModel, table=True):
    __tablename__ = "test_feature_flag"
    __onesite__ = {
        "actions": {
            "toggle_enabled": {"toggle": "enabled", "permissions": "da"},
        },
    }

    id: int | None = Field(default=None, primary_key=True)
    enabled: bool = True


class ConditionalFeatureFlag(SQLModel, table=True):
    __tablename__ = "test_conditional_feature_flag"
    __onesite__ = {
        "actions": {
            "toggle_enabled": {
                "toggle": "enabled",
                "permissions": "da",
                "condition": {"field": "status", "op": "eq", "value": "draft"},
            },
        },
    }

    id: int | None = Field(default=None, primary_key=True)
    enabled: bool = True
    status: str = "draft"


def _model():
    result = get_model_fields(FeatureFlag, "feature_flag")
    return _build_model_dict("FeatureFlag", "feature_flag", "feature_flag", result)


def test_toggle_action_expands_to_the_existing_boolean_inversion():
    action = _model().actions["toggle_enabled"]

    assert action["toggle"] == "enabled"
    assert action["data"] == {"enabled": "!{{value}}"}
    assert action["permissions"] == "da"


def test_toggle_action_renders_a_dynamic_enable_disable_label():
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    page = Environment(loader=FileSystemLoader(template_dir)).get_template(
        "frontend_page_list.tsx.j2"
    ).render(model=_model())

    assert "t('common.disable', 'Disable')" in page
    assert "t('common.enable', 'Enable')" in page
    assert '(item as any)["enabled"]' in page
    assert 'variant={(item as any)["enabled"] ? "destructive" : "default"}' in page


def test_toggle_action_locales_include_enable_and_disable(tmp_path):
    generate_locale_files([], tmp_path)

    assert json.loads((tmp_path / "en.json").read_text())["common"]["enable"] == "Enable"
    assert json.loads((tmp_path / "zh.json").read_text())["common"]["disable"] == "停用"


def test_toggle_action_keeps_declarative_condition_checks():
    result = get_model_fields(ConditionalFeatureFlag, "conditional_feature_flag")
    model = _build_model_dict(
        "ConditionalFeatureFlag",
        "conditional_feature_flag",
        "conditional_feature_flag",
        result,
    )
    action_config = model.actions["toggle_enabled"]

    assert action_config["condition"] == {
        "field": "status",
        "op": "eq",
        "value": "draft",
    }

    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    env = Environment(loader=FileSystemLoader(template_dir))
    api = env.get_template("api.py.j2").render(model=model)
    page = env.get_template("frontend_page_list.tsx.j2").render(model=model)

    assert 'condition = action_data.get("condition")' in api
    assert 'const cond = {"field": "status", "op": "eq", "value": "draft"}' in page
