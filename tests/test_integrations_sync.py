from onesite.codegen.assets import _sync_project_integrations


def test_sync_project_integrations_copies_custom_adapter(tmp_path):
    source = tmp_path / "app" / "integrations"
    source.mkdir(parents=True)
    (source / "device_timeseries.py").write_text(
        "async def write_device_field(**kwargs):\n    return None\n",
        encoding="utf-8",
    )
    backend = tmp_path / "generated" / "backend"

    _sync_project_integrations(tmp_path, backend)

    generated = backend / "app" / "integrations" / "device_timeseries.py"
    assert generated.read_text(encoding="utf-8") == (
        "async def write_device_field(**kwargs):\n    return None\n"
    )
    assert (backend / "app" / "integrations" / "__init__.py").exists()


def test_sync_project_integrations_removes_stale_adapter(tmp_path):
    backend = tmp_path / "generated" / "backend"
    stale = backend / "app" / "integrations" / "stale.py"
    stale.parent.mkdir(parents=True)
    stale.write_text("stale = True\n", encoding="utf-8")

    _sync_project_integrations(tmp_path, backend)

    assert not stale.exists()
