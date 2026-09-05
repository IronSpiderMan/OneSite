"""Model CRUD permissions, field CRU permissions, and frontend visibility."""

from typing import Any


ROLE_ORDER = ["user", "admin", "developer"]


ROLE_LEVELS = {"user": 0, "admin": 1, "developer": 2}


def _parse_model_permissions(raw: Any, model_name: str) -> dict[str, str]:
    """Layer 1: Parse model-level CRUD permissions.

    Returns a dict like {"user": "crud", "admin": "crud", "developer": "crud"}.
    """
    if isinstance(raw, dict):
        return {role: raw.get(role, "") for role in ROLE_ORDER}

    if isinstance(raw, str):
        # String format: "admin-crud", "crud", "rcud"
        parts = raw.split("-", 1)
        if len(parts) == 2:
            prefix_role, perm_chars = parts
        else:
            prefix_role, perm_chars = "user", parts[0]

        min_level = ROLE_LEVELS.get(prefix_role, 0)
        return {
            role: perm_chars if ROLE_LEVELS[role] >= min_level else ""
            for role in ROLE_ORDER
        }

    # Default: full access for all
    return {role: "crud" for role in ROLE_ORDER}


def _compute_flat_perms(role_permissions: dict[str, str]) -> str:
    """Derive a flat permission string as the UNION of all roles' permissions.

    Used for backward-compat template code — includes any permission character
    that at least one role possesses, so schemas include all fields that any
    role can access.
    """
    canonical_order = "crud"
    chars: set[str] = set()
    for perms in role_permissions.values():
        chars.update(perms)
    return "".join(c for c in canonical_order if c in chars)


def _parse_visible(raw: Any, role_permissions: dict[str, str] | None = None) -> dict[str, bool]:
    """Layer 3: Parse frontend visibility config.

    Config formats (in priority order):
      list:  ["admin", "developer"]   → only those roles can see it
      dict:  {"user": True, "admin": True, "developer": False}
      string legacy: "admin"  → admin+ visible

    Default fallback: a role is visible if it has any model-level permission.
    This keeps backward compat — models with restricted permissions are
    automatically hidden from unauthorized roles unless explicitly overridden.
    """
    if isinstance(raw, list):
        return {role: role in raw for role in ROLE_ORDER}

    if isinstance(raw, dict):
        return {role: bool(raw.get(role, False)) for role in ROLE_ORDER}

    if isinstance(raw, str) and raw in ROLE_ORDER:
        min_idx = ROLE_ORDER.index(raw)
        return {role: i >= min_idx for i, role in enumerate(ROLE_ORDER)}

    # Default: visible if role has any model permission
    if role_permissions is not None:
        return {role: bool(role_permissions.get(role, "")) for role in ROLE_ORDER}
    return {role: True for role in ROLE_ORDER}


def _parse_field_permissions(
    raw: Any,
    model_role_permissions: dict[str, str],
    field_name: str,
) -> tuple[dict[str, str], str]:
    """Layer 2: Parse field-level CRU permissions.

    Returns (field_role_permissions, flat_permission_string).

    Inherits from model-level when not set, strips 'd' (delete is model-level).
    Special defaults for id (hidden), created_at (r), updated_at (ru).
    """
    # Special field defaults
    if raw is None:
        if field_name == "id":
            return {role: "" for role in ROLE_ORDER}, ""
        if field_name == "created_at":
            return {role: "r" for role in ROLE_ORDER}, "r"
        if field_name == "updated_at":
            return {role: "ru" for role in ROLE_ORDER}, "ru"

    if raw is None:
        # Inherit from model-level, strip 'd'
        result = {
            role: perms.replace("d", "")
            for role, perms in model_role_permissions.items()
        }
    elif isinstance(raw, dict):
        # Per-role dict: missing roles inherit from model, strip 'd'
        result = {}
        for role in ROLE_ORDER:
            perms = raw.get(role, model_role_permissions.get(role, ""))
            result[role] = perms.replace("d", "")
    elif isinstance(raw, str):
        perms = raw.replace("d", "")
        result = {role: perms for role in ROLE_ORDER}
    else:
        result = {role: "cru" for role in ROLE_ORDER}

    flat = _compute_flat_perms(result)
    return result, flat
