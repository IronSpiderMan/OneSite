"""Normalization of model operation tracking declarations."""

from typing import Any


TRACK_CRUD_OPERATIONS = {
    "c": "create",
    "r": "read",
    "u": "update",
    "d": "delete",
}


TRACK_EXTENDED_OPERATIONS = {"bulk_delete", "import", "export"}


def _normalize_tracked_operations(raw: Any, *, model_name: str) -> list[str]:
    """Validate ``site_props.track`` and return stable operation names."""
    if raw in (None, False, ""):
        return []

    tokens: list[str]
    if isinstance(raw, str):
        if any(char not in TRACK_CRUD_OPERATIONS for char in raw):
            raise ValueError(
                f"Model '{model_name}': track string must contain only c, r, u, d"
            )
        tokens = list(raw)
    elif isinstance(raw, list):
        tokens = raw
    else:
        raise ValueError(
            f"Model '{model_name}': track must be a CRUD string or a list"
        )

    operations: set[str] = set()
    for token in tokens:
        if token == "crud":
            operations.update(TRACK_CRUD_OPERATIONS.values())
        elif token in TRACK_CRUD_OPERATIONS:
            operations.add(TRACK_CRUD_OPERATIONS[token])
        elif token in TRACK_EXTENDED_OPERATIONS:
            operations.add(token)
        else:
            supported = "crud, c, r, u, d, bulk_delete, import, export"
            raise ValueError(
                f"Model '{model_name}': unsupported track operation {token!r}; "
                f"use one of: {supported}"
            )

    order = ("create", "read", "update", "delete", "bulk_delete", "import", "export")
    return [operation for operation in order if operation in operations]
