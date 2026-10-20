"""Model imports are isolated between generated projects."""

import sys
from pathlib import Path

import pytest

from onesite.codegen.model_imports import ModelIntrospectionError
from onesite.codegen.phases.introspect_models import phase_introspect


def _write_model(
    backend: Path,
    *,
    class_name: str,
    table_name: str,
    field_name: str,
) -> None:
    models = backend / "app" / "models"
    models.mkdir(parents=True)
    (backend / "app" / "__init__.py").write_text("", encoding="utf-8")
    (models / "__init__.py").write_text("", encoding="utf-8")
    (models / "thing.py").write_text(
        "from sqlmodel import Field, SQLModel\n\n"
        f"class {class_name}(SQLModel, table=True):\n"
        f"    __tablename__ = {table_name!r}\n"
        "    id: int = Field(primary_key=True)\n"
        f"    {field_name}: str\n",
        encoding="utf-8",
    )


def test_consecutive_projects_do_not_reuse_cached_app_modules(tmp_path):
    first_backend = tmp_path / "first" / "generated" / "backend"
    second_backend = tmp_path / "second" / "generated" / "backend"
    _write_model(
        first_backend,
        class_name="FirstThing",
        table_name="shared_thing",
        field_name="first_value",
    )
    _write_model(
        second_backend,
        class_name="SecondThing",
        table_name="shared_thing",
        field_name="second_value",
    )
    original_path = list(sys.path)

    first = phase_introspect(first_backend)
    second = phase_introspect(second_backend)

    assert first[0]["table_name"] == "shared_thing"
    assert second[0]["table_name"] == "shared_thing"
    assert {field["name"] for field in second[0]["fields"]} >= {
        "id",
        "second_value",
    }
    assert sys.path == original_path


def test_broken_model_import_is_an_explicit_failure(tmp_path):
    backend = tmp_path / "generated" / "backend"
    models = backend / "app" / "models"
    models.mkdir(parents=True)
    (backend / "app" / "__init__.py").write_text("", encoding="utf-8")
    (models / "__init__.py").write_text("", encoding="utf-8")
    (models / "broken.py").write_text(
        "raise RuntimeError('broken model import')\n",
        encoding="utf-8",
    )

    with pytest.raises(ModelIntrospectionError, match="broken model import"):
        phase_introspect(backend)
