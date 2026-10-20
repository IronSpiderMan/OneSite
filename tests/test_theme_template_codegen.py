"""Regression coverage for build-time theme template families."""

import json
from pathlib import Path

import pytest

from onesite.codegen.assets import _sync_frontend_theme_assets
from onesite.codegen.render import (
    TEMPLATE_DIR,
    create_template_environment,
    generate_theme_file,
)
from onesite.codegen.theme import THEMES


THEMED_PAGES = {
    "frontend_page_list.tsx.j2",
    "frontend_page_detail.tsx.j2",
    "frontend_page_create.tsx.j2",
    "singleton_page.tsx.j2",
    "dashboard_page.tsx.j2",
    "settings_page.tsx.j2",
    "profile.tsx.j2",
    "index.css.j2",
}


def test_every_theme_has_an_independent_frontend_template_family():
    for theme_name in THEMES:
        theme_dir = TEMPLATE_DIR / "themes" / theme_name
        assert theme_dir.is_dir()
        assert THEMED_PAGES <= {path.name for path in theme_dir.iterdir()}


@pytest.mark.parametrize("theme_name", THEMES)
def test_theme_loader_prefers_override_and_supports_common_prefix(theme_name):
    environment = create_template_environment(theme_name)

    themed = environment.get_template("frontend_page_detail.tsx.j2")
    shared = environment.get_template("common/frontend_page_detail.tsx.j2")

    assert Path(themed.filename).parent.name == theme_name
    assert Path(shared.filename).parent == TEMPLATE_DIR


def test_theme_loader_falls_back_to_shared_templates():
    environment = create_template_environment("neuron")
    backend_template = environment.get_template("schema.py.j2")

    assert Path(backend_template.filename).parent == TEMPLATE_DIR


def test_generate_theme_css_includes_shared_and_selected_structural_rules(tmp_path):
    output = tmp_path / "index.css"
    theme = THEMES["neuron"]

    generate_theme_file(
        "index.css.j2",
        {"theme": theme, "themes": THEMES, "radius": theme["radius"]},
        output,
        "neuron",
    )

    stylesheet = output.read_text(encoding="utf-8")
    assert ':root[data-theme="neuron"]' in stylesheet
    assert '[data-codegen-theme="neuron"]' in stylesheet
    assert '[data-page-region="detail-grid"]' in stylesheet
def test_normal_theme_overlays_ant_design_adapters_and_dependency(tmp_path):
    frontend_templates = TEMPLATE_DIR.parent / "frontend"
    target = tmp_path / "frontend"
    target.mkdir()
    (target / "package.json").write_text(
        json.dumps({"dependencies": {"react": "^18.2.0"}}),
        encoding="utf-8",
    )

    _sync_frontend_theme_assets(
        frontend_templates,
        target,
        {"style": "normal"},
    )

    package = json.loads((target / "package.json").read_text(encoding="utf-8"))
    button = (target / "src" / "components" / "ui" / "button.tsx").read_text(encoding="utf-8")
    table = (target / "src" / "components" / "ui" / "table.tsx").read_text(encoding="utf-8")
    main = (target / "src" / "main.tsx").read_text(encoding="utf-8")

    assert package["dependencies"]["antd"].startswith("^6.")
    assert "Button as AntButton" in button
    assert "flattenButtonChildren" in button
    assert "icon={icon}" in button
    assert "className={cn('w-full', className)}" in table
    assert "style={{ width: '100%', ...style }}" in table
    assert "AntdThemeProvider" in main
    assert "antd/dist/reset.css" in main


def test_non_normal_theme_does_not_add_ant_design(tmp_path):
    frontend_templates = TEMPLATE_DIR.parent / "frontend"
    target = tmp_path / "frontend"
    target.mkdir()
    (target / "package.json").write_text(
        json.dumps({"dependencies": {"react": "^18.2.0"}}),
        encoding="utf-8",
    )

    _sync_frontend_theme_assets(
        frontend_templates,
        target,
        {"style": "industrial"},
    )

    package = json.loads((target / "package.json").read_text(encoding="utf-8"))
    assert "antd" not in package["dependencies"]
    assert not (target / "src" / "components" / "AntdThemeProvider.tsx").exists()


def test_switching_away_from_normal_removes_exclusive_theme_assets(tmp_path):
    frontend_templates = TEMPLATE_DIR.parent / "frontend"
    target = tmp_path / "frontend"
    (target / "src" / "components").mkdir(parents=True)
    (target / "package.json").write_text(
        json.dumps({"dependencies": {"react": "^18.2.0"}}), encoding="utf-8"
    )
    _sync_frontend_theme_assets(frontend_templates, target, {"style": "normal"})
    assert (target / "src" / "components" / "AntdThemeProvider.tsx").exists()
    _sync_frontend_theme_assets(frontend_templates, target, {"style": "neuron"})
    assert not (target / "src" / "components" / "AntdThemeProvider.tsx").exists()
    package = json.loads((target / "package.json").read_text(encoding="utf-8"))
    assert "antd" not in package["dependencies"]


def test_normal_button_layout_does_not_override_responsive_visibility():
    stylesheet = (TEMPLATE_DIR / "themes" / "normal" / "index.css.j2").read_text(
        encoding="utf-8"
    )

    assert "display: inline-flex !important" not in stylesheet
    assert "flex-direction: row !important" in stylesheet
