"""Shared SQLModel and Pydantic field inspection helpers."""

import inspect
from types import UnionType
from typing import Any, Dict, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic_core import PydanticUndefined
from sqlmodel import SQLModel


def _is_pydantic_model(cls: Any) -> bool:
    """Check if cls is a Pydantic model suitable for JSON schema (excludes DB-backed SQLModels).

    Returns True for plain BaseModel subclasses and SQLModel(table=False),
    but not for SQLModel(table=True) which are real DB tables.
    """
    return (
        inspect.isclass(cls)
        and issubclass(cls, BaseModel)
        and not (issubclass(cls, SQLModel) and getattr(cls, "__table__", None) is not None)
    )


def _unwrap_optional(annotation: Any) -> tuple[Any, bool]:
    """Return the value type inside ``Optional[T]``/``T | None``.

    ``typing.Optional`` and the PEP 604 ``| None`` syntax have different
    origins at runtime.  Treating only ``typing.Union`` as optional caused
    otherwise typed JSON fields to fall through to the string fallback.
    """
    if get_origin(annotation) in (Union, UnionType):
        value_types = [item for item in get_args(annotation) if item is not type(None)]
        if len(value_types) == 1 and len(value_types) != len(get_args(annotation)):
            return value_types[0], True
    return annotation, False


def _get_numeric_bounds(field: Any) -> tuple[Any, Any]:
    """Extract inclusive Pydantic ``ge``/``le`` constraints from FieldInfo."""
    minimum = maximum = None
    for constraint in getattr(field, "metadata", ()) or ():
        if getattr(constraint, "ge", None) is not None:
            minimum = constraint.ge
        if getattr(constraint, "le", None) is not None:
            maximum = constraint.le
    return minimum, maximum


def _get_field_site_props(field: Any) -> Dict[str, Any]:
    """Return OneSite field metadata from SQLModel or Pydantic field info.

    JSON child models are usually ``SQLModel(table=False)`` instances.  They
    do not have a SQL column of their own, but SQLModel still preserves
    ``sa_column_kwargs`` on their FieldInfo, making it the most consistent
    place for nested JSON UI metadata.
    """
    sa_column_kwargs = getattr(field, "sa_column_kwargs", {})
    if sa_column_kwargs is PydanticUndefined or not isinstance(sa_column_kwargs, dict):
        sa_column_kwargs = {}
    info = sa_column_kwargs.get("info", {})
    if not isinstance(info, dict):
        info = {}
    site_props = info.get("site_props", {})
    if not isinstance(site_props, dict):
        site_props = {}
    if "group" in info and not site_props.get("group"):
        site_props = {**site_props, "group": info["group"]}

    if site_props:
        return site_props

    for extra_name in ("json_schema_extra", "schema_extra"):
        extra = getattr(field, extra_name, None)
        if extra is PydanticUndefined or not isinstance(extra, dict):
            continue
        props = extra.get("site_props", {})
        if isinstance(props, dict) and props:
            return props

    sa_column = getattr(field, "sa_column", None)
    if sa_column is not None and sa_column is not PydanticUndefined:
        column_info = getattr(sa_column, "info", {})
        if isinstance(column_info, dict):
            props = column_info.get("site_props", {})
            if isinstance(props, dict):
                return props
    return {}
