from pathlib import Path

import pytest

from onesite.codegen.phases.finalize_standalone import (
    StandaloneModelError,
    phase_finalize_standalone,
)
from onesite.codegen.phases.introspect_models import phase_introspect
from onesite.codegen.phases.sync_models import phase_sync_models


def test_introspection_imports_nested_model_support_packages(tmp_path: Path):
    model_dir = tmp_path / "app" / "models"
    enum_dir = model_dir / "enums"
    enum_dir.mkdir(parents=True)
    (enum_dir / "__init__.py").write_text("", encoding="utf-8")
    (enum_dir / "alarm.py").write_text(
        "from enum import StrEnum\n\n"
        "class Level(StrEnum):\n"
        "    HIGH = 'high'\n",
        encoding="utf-8",
    )
    (model_dir / "alarm.py").write_text(
        "from sqlmodel import Field, SQLModel\n"
        "from .enums.alarm import Level\n\n"
        "class Alarm(SQLModel, table=True):\n"
        "    id: int | None = Field(default=None, primary_key=True)\n"
        "    level: Level = Field(default=Level.HIGH)\n",
        encoding="utf-8",
    )
    backend_path = tmp_path / "generated" / "backend"

    phase_sync_models(tmp_path, backend_path)
    models = phase_introspect(backend_path)

    assert any(model["name"] == "Alarm" for model in models)


def test_generated_models_use_local_action_runtime(tmp_path: Path):
    model_dir = tmp_path / "app" / "models"
    model_dir.mkdir(parents=True)
    (model_dir / "job.py").write_text(
        "from onesite_runtime import ActionContext, action\n"
        "\n"
        "class Job:\n"
        "    @action\n"
        "    def run(self, *, context: ActionContext):\n"
        "        pass\n",
        encoding="utf-8",
    )

    backend_path = tmp_path / "generated" / "backend"
    phase_sync_models(tmp_path, backend_path)
    phase_finalize_standalone(backend_path)

    generated = (backend_path / "app" / "models" / "job.py").read_text(
        encoding="utf-8"
    )
    assert "from app.core.action_runtime import ActionContext, action" in generated
    assert "onesite_runtime" not in generated


def test_generated_models_rewrite_module_style_action_import(tmp_path: Path):
    model_dir = tmp_path / "app" / "models"
    model_dir.mkdir(parents=True)
    (model_dir / "job.py").write_text(
        "import onesite_runtime\n"
        "\n"
        "@onesite_runtime.action\n"
        "def run():\n"
        "    pass\n",
        encoding="utf-8",
    )

    backend_path = tmp_path / "generated" / "backend"
    phase_sync_models(tmp_path, backend_path)
    phase_finalize_standalone(backend_path)

    generated = (backend_path / "app" / "models" / "job.py").read_text(
        encoding="utf-8"
    )
    assert "from app.core import action_runtime as onesite_runtime" in generated
    assert "import onesite_runtime\n" not in generated


def test_action_metadata_is_introspected_before_runtime_import_is_rewritten(tmp_path: Path):
    model_dir = tmp_path / "app" / "models"
    model_dir.mkdir(parents=True)
    (model_dir / "job.py").write_text(
        "from sqlmodel import Field, SQLModel\n"
        "from onesite_runtime import action\n"
        "\n"
        "class Job(SQLModel, table=True):\n"
        "    id: int | None = Field(default=None, primary_key=True)\n"
        "\n"
        "    @action\n"
        "    def run(self):\n"
        "        pass\n",
        encoding="utf-8",
    )
    backend_path = tmp_path / "generated" / "backend"

    phase_sync_models(tmp_path, backend_path)
    models = phase_introspect(backend_path)

    job = next(model for model in models if model["name"] == "Job")
    assert job["actions"]["run"]["function"] is True

    phase_finalize_standalone(backend_path)
    generated = (backend_path / "app" / "models" / "job.py").read_text(encoding="utf-8")
    assert "from app.core.action_runtime import action" in generated


def test_finalize_removes_typed_config_import_and_metadata(tmp_path: Path):
    model_dir = tmp_path / "app" / "models"
    model_dir.mkdir(parents=True)
    model_path = model_dir / "article.py"
    model_path.write_text(
        "from onesite.config import OneSiteConfig\n"
        "from sqlmodel import SQLModel\n"
        "\n"
        "class Article(SQLModel):\n"
        "    __onesite__ = OneSiteConfig(page_edit=True)\n"
        "    title: str\n",
        encoding="utf-8",
    )

    phase_finalize_standalone(tmp_path)

    generated = model_path.read_text(encoding="utf-8")
    assert "onesite" not in generated
    assert "title: str" in generated


def test_finalize_removes_module_style_config_import(tmp_path: Path):
    model_dir = tmp_path / "app" / "models"
    model_dir.mkdir(parents=True)
    model_path = model_dir / "article.py"
    model_path.write_text(
        "import onesite.config as site_config\n"
        "\n"
        "class Article:\n"
        "    __onesite__ = site_config.OneSiteConfig(page_edit=True)\n",
        encoding="utf-8",
    )

    phase_finalize_standalone(tmp_path)

    assert "onesite" not in model_path.read_text(encoding="utf-8")


def test_finalize_rejects_runtime_use_of_config_symbols(tmp_path: Path):
    model_dir = tmp_path / "app" / "models"
    model_dir.mkdir(parents=True)
    (model_dir / "invalid.py").write_text(
        "from onesite.config import OneSiteConfig\n"
        "config_type = OneSiteConfig\n",
        encoding="utf-8",
    )

    with pytest.raises(StandaloneModelError, match="outside __onesite__"):
        phase_finalize_standalone(tmp_path)
