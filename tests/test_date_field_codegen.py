"""Regression coverage for date-only model fields."""

from datetime import date, datetime, time
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict


class DateModel(SQLModel, table=True):
    __tablename__ = "test_date_model"

    id: Optional[int] = Field(default=None, primary_key=True)
    due_date: date
    starts_on: date = Field(default_factory=date.today)
    opens_at: time = time(0, 0, 0)
    reviewed_on: Optional[date] = None
    priority: Optional[int] = None
    custom_dates: list[datetime] = Field(default_factory=list, sa_column=Column(JSON))


def test_date_fields_generate_date_only_inputs_and_schema_imports():
    result = get_model_fields(DateModel, "date_model")
    model = _build_model_dict("DateModel", "date_model", "date_model", result)
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    environment = Environment(loader=FileSystemLoader(template_dir))

    fields = {field.name: field for field in result.fields}
    assert fields["due_date"].type == "date"
    assert fields["due_date"].ui_type == "date"
    assert fields["starts_on"].default_factory == "date"
    assert fields["reviewed_on"].type == "Optional[date]"
    assert fields["reviewed_on"].ui_type == "date"
    assert fields["custom_dates"].type == "List[datetime]"
    assert fields["custom_dates"].ui_type == "json"
    assert fields["custom_dates"].json_item_kind == "datetime"

    schema = environment.get_template("schema.py.j2").render(model=model)
    create_page = environment.get_template("frontend_page_create.tsx.j2").render(model=model)

    assert "from datetime import datetime, date" in schema
    assert "starts_on: Optional[date] = None" in schema
    assert "opens_at: time = time.fromisoformat('00:00:00')" in schema
    assert 'id="due_date"' in create_page
    assert 'type="date"' in create_page
    assert "defaultValue={new Date().toLocaleDateString('en-CA')}" in create_page
    assert 'type="datetime-local"' not in create_page
    assert "def _empty_optional_scalar_strings_to_none" in schema
    assert "for field_name in ['starts_on', 'reviewed_on', 'priority']:" in schema


def test_datetime_arrays_generate_a_picker_per_json_element():
    result = get_model_fields(DateModel, "date_model")
    model = _build_model_dict("DateModel", "date_model", "date_model", result)
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    environment = Environment(loader=FileSystemLoader(template_dir))
    page = environment.get_template("frontend_page_create.tsx.j2").render(model=model)
    crud = environment.get_template("crud.py.j2").render(model=model)

    assert '<JsonScalarArrayEditor itemKind="datetime" value={value} onChange={onChange} />' in page
    assert "def _serialize_json_scalar_arrays(data: dict) -> dict:" in crud
    assert "to_utc(value).isoformat() if isinstance(value, datetime) else value" in crud
    assert "obj_in.dict(exclude_none=True)" in crud


def test_datetime_crud_normalization_matches_column_timezone_awareness():
    class TimestampModel(SQLModel, table=True):
        __tablename__ = "test_timestamp_model"

        id: Optional[int] = Field(default=None, primary_key=True)
        observed_at: datetime

    result = get_model_fields(TimestampModel, "timestamp_model")
    model = _build_model_dict("TimestampModel", "timestamp_model", "timestamp_model", result)
    template_dir = Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    environment = Environment(loader=FileSystemLoader(template_dir))
    crud = environment.get_template("crud.py.j2").render(model=model)

    assert "def _datetime_column_uses_timezone(field_name: str) -> bool:" in crud
    assert "normalized.replace(tzinfo=None)" in crud
    assert "if value.tzinfo is not None or _datetime_column_uses_timezone" in crud
