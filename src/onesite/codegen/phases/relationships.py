"""Phase 4 — Relationship resolution.

Enriches each :class:`~onesite.codegen.types.ModelDefinition` with
resolved foreign-key labels, reverse-FK references, many-to-many
connections via link tables, and timeseries parent-child links.

.. note::

   This phase **mutates** the model dicts in place by adding keys that
   are consumed by the Jinja2 template rendering phases.
"""

from typing import Any

from ..types import ModelDefinition
from .base import ROLE_ORDER, ROLE_TO_ENUM, console, pluralize


# ── Min-role computation ─────────────────────────────────────────────────


def _resolve_min_roles(models: list[ModelDefinition]) -> None:
    """Compute the minimum role level required for each CRUD operation."""

    def _min_role_for(perm_char: str, role_permissions: dict) -> str:
        for role in ROLE_ORDER:
            perms = role_permissions.get(role, "")
            if perm_char in perms:
                return ROLE_TO_ENUM[role]
        return "DEVELOPER"

    for model in models:
        rp = model.get("role_permissions", {})
        model["min_role_for_read"] = _min_role_for("r", rp)
        model["min_role_for_create"] = _min_role_for("c", rp)
        model["min_role_for_update"] = _min_role_for("u", rp)
        model["min_role_for_delete"] = _min_role_for("d", rp)


# ── Link-table flags ─────────────────────────────────────────────────────


def _init_link_table_flags(models: list[ModelDefinition]) -> None:
    """Set link-table-related fields and ``show_in_menu`` for every model."""
    for model in models:
        model.setdefault("m2m_fields", [])
        model.setdefault("reverse_m2m", [])
        model["reverse_foreign_keys"] = []

        if model.get("is_link_table"):
            order_field = next(
                (f for f in model["fields"] if f["name"] == "order" and not f.get("fk_info")),
                None,
            )
            model["link_order_field"] = "order" if order_field else None

            link_extra_fields = [
                f for f in model["fields"]
                if not f.get("fk_info") and f["name"] not in ("id", "order")
            ]
            model["link_extra_fields"] = link_extra_fields
            model["is_association_table"] = len(link_extra_fields) > 0
        else:
            model["link_order_field"] = None
            model["link_extra_fields"] = []
            model["is_association_table"] = False

        # Validate owner_field: must be an FK field pointing to User
        owner_field = model.get("owner_field")
        if owner_field:
            fk_names = {fk["name"] for fk in model["foreign_keys"]}
            if owner_field not in fk_names:
                console.print(
                    f"[yellow]Warning: Model '{model['name']}' has owner_field='{owner_field}' "
                    f"but no matching FK field found. Owner filtering disabled.[/yellow]"
                )
                model["owner_field"] = None
            else:
                fk = next((fk for fk in model["foreign_keys"] if fk["name"] == owner_field), None)
                if fk and fk["target_model"] != "User":
                    console.print(
                        f"[yellow]Warning: Model '{model['name']}' owner_field='{owner_field}' "
                        f"targets '{fk['target_model']}', not 'User'. Owner filtering disabled.[/yellow]"
                    )
                    model["owner_field"] = None

        if model.get("is_link_table") and model.get("is_association_table"):
            model["show_in_menu"] = bool(
                model.get("site_props", {}).get("show_in_menu", True)
            )
        else:
            model["show_in_menu"] = True


# ── FK label resolution & reverse FK ─────────────────────────────────────


def _resolve_fk_labels_and_reverse(
    models: list[ModelDefinition], model_map: dict
) -> None:
    """Label FK targets and populate ``reverse_foreign_keys`` on target models."""
    model_map_lower: dict[str, dict] = {k.lower(): v for k, v in model_map.items()}
    source_mod_map: dict[str, dict] = {
        m["source_module"]: m for m in models if m.get("source_module")
    }

    for model in models:
        for fk in model["foreign_keys"]:
            target_model = model_map.get(fk["target_model"])
            if target_model is None:
                target_model = model_map_lower.get(fk["target_model"].lower())
                if target_model is not None:
                    fk["target_model"] = target_model["name"]
            if target_model is None:
                target_model = source_mod_map.get(fk["target_service"])
                if target_model is not None:
                    fk["target_model"] = target_model["name"]
            if target_model is None:
                continue

            fk["target_service"] = target_model["module_name"]
            fk["target_source_module"] = target_model["source_module"]
            fk["target_endpoint"] = f"{target_model['module_name']}s"

            fk["label_field"] = (
                target_model.get("unique_search_field") or target_model["search_field"]
            )
            fk["target_readable_fields"] = [
                f for f in target_model["fields"]
                if "r" in f["permissions"]
                and f["name"] != "password"
                and not f.get("fk_info")
            ]

            if model.get("is_link_table") or model.get("is_timescaledb") or model.get("is_latest_table") or model["name"] == target_model["name"]:
                continue

            reverse_name = pluralize(model["module_name"])

            source_readable_fields = [
                f for f in model["fields"]
                if "r" in f["permissions"]
                and f["name"] != "password"
            ]

            target_model["reverse_foreign_keys"].append({
                "name": reverse_name,
                "source_model": model["name"],
                "source_service": model["module_name"],
                "source_fk_field": fk["name"],
                "label_field": model.get("unique_search_field") or model["search_field"],
                "display": fk.get("reverse_display", True),
                "source_readable_fields": source_readable_fields,
            })


# ── M2M resolution ───────────────────────────────────────────────────────


def _resolve_m2m(
    models: list[ModelDefinition], model_map: dict, module_map: dict
) -> None:
    """Resolve many-to-many relationships through link tables."""
    for model in models:
        if not model.get("is_link_table"):
            continue

        fks = model["foreign_keys"]
        if len(fks) < 2:
            continue

        m2m_cfg = {}
        if isinstance(model.get("site_props"), dict):
            m2m_cfg = model["site_props"].get("m2m", {}) or {}

        directions = m2m_cfg.get("directions")
        if not isinstance(directions, list) or not directions:
            directions = [
                {
                    "from": fks[0]["target_service"],
                    "to": fks[1]["target_service"],
                    "editable": True,
                }
            ]

        editable_edges = {
            (str(d.get("from", "")), str(d.get("to", "")))
            for d in directions
            if isinstance(d, dict) and d.get("editable", True)
        }

        for d in directions:
            _apply_m2m_direction(d, model, fks, models, model_map, module_map, editable_edges)


def _apply_m2m_direction(
    d: Any,
    link_model: ModelDefinition,
    link_fks: list,
    all_models: list[ModelDefinition],
    model_map: dict,
    module_map: dict,
    editable_edges: set,
) -> None:
    """Apply a single M2M direction config (one edge in the link table graph)."""
    if not isinstance(d, dict):
        return

    from_ref = str(d.get("from", "")).strip()
    to_ref = str(d.get("to", "")).strip()
    if not from_ref or not to_ref:
        return

    from_model = module_map.get(from_ref) or model_map.get(from_ref)
    to_model = module_map.get(to_ref) or model_map.get(to_ref)
    if not from_model or not to_model:
        return

    def _find_fk_for(target_service: str, target_model: str):
        return next(
            (fk for fk in link_fks if fk.get("target_service") == target_service or fk.get("target_model") == target_model),
            None,
        )

    from_fk = _find_fk_for(from_model["module_name"], from_model["name"])
    to_fk = _find_fk_for(to_model["module_name"], to_model["name"])
    if not from_fk or not to_fk:
        return

    # Forward direction: add m2m_field to from_model
    if d.get("editable", True):
        m2m_field_name = f"{to_model['lower_name']}_ids"
        existing = next(
            (x for x in from_model.get("m2m_fields", [])
             if x.get("name") == m2m_field_name and x.get("target_model") == to_model["name"]),
            None,
        )
        if existing is None:
            from_model["m2m_fields"].append({
                "name": m2m_field_name,
                "target_model": to_model["name"],
                "target_service": to_model["module_name"],
                "target_endpoint": f"{to_model['module_name']}s",
                "label_field": (
                    to_model.get("unique_search_field") or to_model["search_field"]
                ),
                "target_readable_fields": [
                    f for f in to_model["fields"]
                    if "r" in f["permissions"] and f["name"] != "password"
                ],
                "target_fk_fields": [
                    {"name": fk["name"], "target_model": fk["target_model"],
                     "target_source_module": fk["target_source_module"],
                     "label_field": fk["label_field"]}
                    for fk in to_model.get("foreign_keys", [])
                    if fk.get("target_source_module")
                ],
                "link_model": link_model["name"],
                "link_module": link_model["source_module"],
                "target_source_module": to_model["source_module"],
                "source_fk_field": from_fk["name"],
                "target_fk_field": to_fk["name"],
                "order_field": link_model.get("link_order_field"),
            })

    # Skip reverse if this edge was explicitly configured as non-reversible
    if (to_model["module_name"], from_model["module_name"]) in editable_edges:
        return

    reverse_name = pluralize(from_model["module_name"])
    existing_reverse = next(
        (x for x in to_model.get("reverse_m2m", [])
         if x.get("name") == reverse_name and x.get("source_model") == from_model["name"]),
        None,
    )
    if existing_reverse is None:
        to_model["reverse_m2m"].append({
            "name": reverse_name,
            "source_model": from_model["name"],
            "source_service": from_model["module_name"],
            "source_endpoint": f"{from_model['module_name']}s",
            "label_field": (
                from_model.get("unique_search_field") or from_model["search_field"]
            ),
            "source_readable_fields": [
                f for f in from_model["fields"]
                if "r" in f["permissions"] and f["name"] != "password"
            ],
            "source_fk_fields": [
                {"name": fk["name"], "target_model": fk["target_model"],
                 "target_source_module": fk["target_source_module"],
                 "label_field": fk["label_field"]}
                for fk in from_model.get("foreign_keys", [])
                if fk.get("target_source_module")
            ],
            "display": to_fk.get("reverse_display", True),
            "link_model": link_model["name"],
            "link_module": link_model["source_module"],
            "source_source_module": from_model["source_module"],
            "source_fk_field": from_fk["name"],
            "target_fk_field": to_fk["name"],
            "order_field": link_model.get("link_order_field"),
        })


# ── TimescaleDB metadata ─────────────────────────────────────────────────


def _resolve_timescaledb_metadata(models: list[ModelDefinition]) -> None:
    """Compute derived fields for timescale models (time column, latest table name)."""
    for model in models:
        if not model.get("is_timescaledb"):
            continue

        time_column = None
        for f in model["fields"]:
            if f["ui_type"] == "datetime":
                if f["name"] in ("reported_at", "created_at"):
                    time_column = f["name"]
                    break
                if time_column is None:
                    time_column = f["name"]
        model["timescaledb_time_column"] = time_column or "created_at"
        model["timescaledb_latest_table_name"] = f"{model['table_name']}_latest"

        entity_field = model.get("timescaledb_entity_field", "")
        for f in model["fields"]:
            if f["name"] == entity_field:
                if f.get("type") == "int":
                    model["timescaledb_entity_sql_type"] = "INTEGER"
                else:
                    model["timescaledb_entity_sql_type"] = "TEXT"
                if f.get("fk_info"):
                    table = (
                        f["fk_info"]["target_service"]
                        or entity_field.replace("_id", "")
                    )
                    model["timescaledb_entity_target_table"] = table
                    model["timescaledb_entity_model"] = f["fk_info"]["target_model"]
                break
        else:
            model["timescaledb_entity_sql_type"] = "INTEGER"
            model["timescaledb_entity_target_table"] = entity_field.replace("_id", "")

        model_table = model.get("timescaledb_model_table", "")
        if model_table:
            from .base import to_pascal
            model["timescaledb_model_class"] = to_pascal(model_table)


def _resolve_timeseries_relations(models: list[ModelDefinition]) -> None:
    """For each timeseries model, build ``reverse_timeseries`` on the parent entity."""
    for model in models:
        model["reverse_timeseries"] = []

    for ts_model in models:
        if not ts_model.get("is_timescaledb"):
            continue

        entity_field = ts_model.get("timescaledb_entity_field")
        if not entity_field:
            continue

        fk_info = None
        for fk in ts_model["foreign_keys"]:
            if fk["name"] == entity_field:
                fk_info = fk
                break

        if not fk_info:
            continue

        target_model_name = fk_info["target_model"]
        for model in models:
            if model["name"] == target_model_name:
                model.setdefault("reverse_timeseries", [])
                model["reverse_timeseries"].append({
                    "model_name": ts_model["name"],
                    "module_name": ts_model["module_name"],
                    "table_name": ts_model["table_name"],
                    "latest_table_name": ts_model.get(
                        "timescaledb_latest_table_name",
                        f"{ts_model['table_name']}_latest",
                    ),
                    "entity_field": entity_field,
                    "entity_model": target_model_name,
                    "metric_field": ts_model.get("timescaledb_metric_field"),
                    "time_field": ts_model.get("timescaledb_time_column", "created_at"),
                    "timescaledb_model_table": ts_model.get("timescaledb_model_table"),
                    "timescaledb_model_class": ts_model.get("timescaledb_model_class"),
                    "api_base": f"{ts_model['module_name']}s",
                    "source_module": ts_model["source_module"],
                })
                break


# ── Public entry point ───────────────────────────────────────────────────


def phase_resolve_relationships(
    models: list[ModelDefinition],
) -> list[ModelDefinition]:
    """Resolve FK labels, reverse FK, and M2M relationships across all models.

    Mutates the model dicts in place (adding relation containers, computed fields),
    then returns the same list for convenience.
    """
    model_map = {m["name"]: m for m in models}
    module_map = {m["module_name"]: m for m in models}

    _resolve_min_roles(models)
    _init_link_table_flags(models)
    _resolve_timescaledb_metadata(models)
    _resolve_timeseries_relations(models)
    _resolve_fk_labels_and_reverse(models, model_map)
    _resolve_m2m(models, model_map, module_map)

    return models
