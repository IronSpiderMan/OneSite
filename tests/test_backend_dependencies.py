"""Backend dependency declarations are retained across generation."""

from onesite.codegen.assets import sync_backend_assets
from onesite.main import _ensure_custom_backend_source


def test_project_extra_requirements_are_merged_without_duplicate_packages(tmp_path):
    backend = tmp_path / "generated" / "backend"
    source = tmp_path / "app"
    source.mkdir(parents=True)
    (source / "requirements.extra.txt").write_text(
        "boto3>=1.35\nhttpx>=0.27,<1\nboto3>=1.35\n",
        encoding="utf-8",
    )

    sync_backend_assets(
        tmp_path,
        backend,
        {
            "allowed_origins": [],
            "extra": {"TIMEZONE": "Asia/Shanghai"},
        },
    )

    requirements = (backend / "requirements.txt").read_text(encoding="utf-8").splitlines()
    assert requirements.count("boto3>=1.35") == 1
    assert "httpx>=0.27,<1" not in requirements
    assert requirements.count("httpx") == 1


def test_project_initialization_creates_extra_requirements_file(tmp_path):
    _ensure_custom_backend_source(tmp_path / "app")

    assert (tmp_path / "app" / "requirements.extra.txt").read_text(encoding="utf-8") == ""
