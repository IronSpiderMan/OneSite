from onesite.codegen.render import TEMPLATE_DIR, create_template_environment


def _render_site_metadata(
    system_model=None, site_name_field=None, logo_field=None
) -> str:
    template = create_template_environment().get_template("site_metadata.tsx.j2")
    return template.render(
        system_model=system_model,
        site_name_field=site_name_field,
        logo_field=logo_field,
    )


def test_site_metadata_uses_runtime_system_config_site_name():
    output = _render_site_metadata(
        system_model={"name": "SystemConfig"},
        site_name_field={"name": "site_name", "is_local_storage": False},
    )

    assert "useSystemConfigStore" in output
    assert "state.data?.site_name" in output
    assert "void fetchData()" in output
    assert "document.title = siteName" in output
    assert "onesite:site_name_updated" in output


def test_site_metadata_falls_back_without_system_config():
    output = _render_site_metadata()

    assert "useSystemConfigStore" not in output
    assert "document.title = siteName" in output
    assert "VITE_PROJECT_NAME" in output


def test_site_metadata_uses_site_logo_as_favicon():
    output = _render_site_metadata(
        system_model={"name": "SystemConfig"},
        logo_field={"name": "logo", "is_local_storage": False},
    )

    assert "link[data-onesite-favicon]" in output
    assert "favicon.rel = 'icon'" in output
    assert "favicon.href = logo" in output
    assert "favicon?.remove()" in output


def test_frontend_shell_displays_the_runtime_site_name():
    frontend_templates = TEMPLATE_DIR.parent / "frontend" / "src"
    app = (frontend_templates / "App.tsx").read_text(encoding="utf-8")
    layout = (frontend_templates / "components" / "Layout.tsx").read_text(
        encoding="utf-8"
    )

    assert "<SiteMetadata />" in app
    assert "localStorage.getItem('onesite_site_name')" in layout
    assert "onesite:site_name_updated" in layout
