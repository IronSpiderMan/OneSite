"""Validate declarative filter defaults before rendering UI code."""

from datetime import date, datetime, time
import math

from .time_filters import RELATIVE_TIME_PERIODS


def validate_filter_default(value, field, context, filter_type=None):
    def fail():
        raise ValueError(f"{context}: invalid filter default {value!r}")

    kind = field.get("ui_type", "str")
    if value is None:
        return None
    if filter_type == "date_range" and kind not in ("date", "datetime"):
        fail()
    if filter_type == "number_range" and kind not in ("int", "float"):
        fail()
    if isinstance(value, dict):
        if set(value) == {"period"}:
            if kind not in ("date", "datetime") or filter_type not in (None, "date_range") or not isinstance(value["period"], str) or value["period"] not in RELATIVE_TIME_PERIODS:
                fail()
            return value
        keys = {"min", "max"} if filter_type == "number_range" else {"start", "end"}
        if not value or not set(value) <= keys or (filter_type not in ("date_range", "number_range") and kind not in ("date", "datetime")):
            fail()
        for bound in value.values():
            if isinstance(bound, (dict, list)):
                fail()
            validate_filter_default(bound, field, context)
        if len(value) == 2 and all(v is not None for v in value.values()):
            lo, hi = ("min", "max") if filter_type == "number_range" else ("start", "end")
            if value[lo] > value[hi]:
                fail()
        return value
    multi = filter_type == "multi_select" or (filter_type is None and field.get("is_multi_select"))
    if multi or (filter_type is None and field.get("is_enum") and isinstance(value, list)):
        if not isinstance(value, list) or any(v is None for v in value):
            fail()
        return [validate_filter_default(v, {**field, "is_multi_select": False}, context, "select") for v in value]
    if isinstance(value, (list, dict)) or filter_type in ("date_range", "number_range"):
        fail()
    if field.get("is_enum"):
        if value not in field.get("enum_values", []):
            fail()
    elif kind == "bool":
        if not isinstance(value, bool):
            fail()
    elif kind in ("int", "float"):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or (kind == "int" and not isinstance(value, int)):
            fail()
    elif kind in ("date", "datetime", "time"):
        try:
            {"date": date, "datetime": datetime, "time": time}[kind].fromisoformat(value)
        except (TypeError, ValueError):
            fail()
    elif not isinstance(value, str):
        fail()
    return value
