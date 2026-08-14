"""Shared relative-time filter vocabulary for Dashboard declarations."""

RELATIVE_TIME_PERIODS = frozenset({
    "today",
    "yesterday",
    "this_week",
    "last_week",
    "this_month",
    "last_month",
    "last_7_days",
    "last_30_days",
})
