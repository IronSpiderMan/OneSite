"""SiteConfig-owned custom backend scaffolding and synchronization coverage."""

import pytest

from onesite.codegen.custom_backend import CustomBackendError, sync_custom_backend
from onesite.codegen.router import update_api_router


def _feature(name="health", **values):
    return {"name": name, "frontend_only": False, "backend_only": False, **values}


def test_configured_backend_is_scaffolded_mirrored_and_registered(tmp_path):
    backend = tmp_path / "generated/backend"
    modules = sync_custom_backend(tmp_path, backend, [_feature()])

    assert modules == ["health"]
    source = tmp_path / "app/backend"
    assert (source / "api/health.py").exists()
    assert (source / "services/health.py").exists()
    assert (source / "cruds/health.py").exists()
    assert (backend / "app/api/endpoints/custom/health.py").exists()

    api_file = backend / "app/api/api.py"
    update_api_router([], api_file, custom_api_modules=modules)
    content = api_file.read_text(encoding="utf-8")
    assert "from app.api.endpoints.custom import health as custom_api_0" in content
    assert "api_router.include_router(custom_api_0.router)" in content


def test_backend_scaffold_never_overwrites_developer_code(tmp_path):
    backend = tmp_path / "generated/backend"
    feature = _feature()
    sync_custom_backend(tmp_path, backend, [feature])
    service = tmp_path / "app/backend/services/health.py"
    service.write_text("VALUE = 'developer owned'\n", encoding="utf-8")

    sync_custom_backend(tmp_path, backend, [feature])

    assert service.read_text(encoding="utf-8") == "VALUE = 'developer owned'\n"
    assert (backend / "app/services/custom/health.py").read_text(encoding="utf-8") == service.read_text(encoding="utf-8")


def test_frontend_only_feature_does_not_generate_backend(tmp_path):
    modules = sync_custom_backend(
        tmp_path,
        tmp_path / "generated/backend",
        [_feature(frontend_only=True)],
    )
    assert modules == []
    assert not (tmp_path / "app/backend/api/health.py").exists()


def test_backend_only_feature_generates_backend(tmp_path):
    modules = sync_custom_backend(
        tmp_path,
        tmp_path / "generated/backend",
        [_feature(backend_only=True)],
    )
    assert modules == ["health"]


def test_unconfigured_router_is_mirrored_but_not_registered(tmp_path):
    api = tmp_path / "app/backend/api/manual.py"
    api.parent.mkdir(parents=True)
    api.write_text("router = object()\n", encoding="utf-8")
    backend = tmp_path / "generated/backend"

    modules = sync_custom_backend(tmp_path, backend, [])

    assert modules == []
    assert (backend / "app/api/endpoints/custom/manual.py").exists()


def test_configured_api_must_keep_top_level_router(tmp_path):
    api = tmp_path / "app/backend/api/health.py"
    api.parent.mkdir(parents=True)
    api.write_text("VALUE = 1\n", encoding="utf-8")
    with pytest.raises(CustomBackendError, match="top-level router"):
        sync_custom_backend(tmp_path, tmp_path / "generated/backend", [_feature()])


def test_custom_backend_removes_stale_generated_files(tmp_path):
    source = tmp_path / "app/backend/services"
    source.mkdir(parents=True)
    current = source / "current.py"
    current.write_text("VALUE = 1\n", encoding="utf-8")
    backend = tmp_path / "generated/backend"
    sync_custom_backend(tmp_path, backend, [])
    current.unlink()
    sync_custom_backend(tmp_path, backend, [])
    assert not (backend / "app/services/custom/current.py").exists()
