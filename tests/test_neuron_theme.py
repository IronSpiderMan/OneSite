"""Regression coverage for the neuron telemetry-console theme."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from onesite.codegen.theme import THEMES, resolve_theme


def test_only_supported_themes_are_registered():
    assert set(THEMES) == {"normal", "industrial", "neuron", "arco"}


def test_neuron_theme_resolves_and_renders_into_generated_css():
    theme, radius = resolve_theme({"style": "neuron"})

    assert theme["id"] == "neuron"
    assert radius == 0.125

    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    template = Environment(loader=FileSystemLoader(template_dir)).get_template("index.css.j2")
    stylesheet = template.render(theme=theme, themes=THEMES, radius=radius)

    assert ':root[data-theme="neuron"]' in stylesheet
    assert ':root[data-theme="neuron"].dark' in stylesheet
    assert 'color-scheme: light;' in stylesheet
    assert '[data-theme="neuron"].dark { color-scheme: dark; }' in stylesheet
    assert 'background-size: 32px 32px;' in stylesheet
    assert '.neuron-brand' in stylesheet
    assert '.settings-panel' in stylesheet
    assert '[data-ui="card"]' in stylesheet


def test_neuron_light_palette_is_distinct_from_its_dark_palette():
    theme = THEMES["neuron"]

    assert theme["background"] != theme["dark_background"]
    assert theme["background"] == "210 25% 97%"
    assert theme["foreground"] == "210 22% 16%"
