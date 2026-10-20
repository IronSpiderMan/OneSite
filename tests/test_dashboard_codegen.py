"""Dashboard generation must follow the configured SystemConfig shape."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def _render_dashboard(show_announcement: bool) -> str:
    template_dir = (
        Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    )
    return Environment(loader=FileSystemLoader(template_dir)).get_template(
        "dashboard_page.tsx.j2"
    ).render(
        models=[],
        scheduled_tasks=[],
        site_logger=False,
        show_dashboard_announcement=show_announcement,
    )


def test_dashboard_omits_announcement_for_system_config_without_field():
    dashboard = _render_dashboard(False)

    assert "systemConfig?.announcement_content" not in dashboard
    assert "systemConfig.announcement_content" not in dashboard


def test_dashboard_renders_announcement_when_field_is_available():
    dashboard = _render_dashboard(True)

    assert "systemConfig?.announcement_content" in dashboard
    assert "systemConfig.announcement_content" in dashboard
