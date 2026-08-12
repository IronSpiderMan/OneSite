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


_RELATION_EDITORS = {"select", "inline", "readonly", "hidden"}


def _inline_field_type(field: dict) -> str:
    """Return a dependency-free type for an inline relation item schema."""
    if field.get("is_enum"):
        return "List[str]" if field.get("is_multi_select") else "str"
    ui_type = field.get("ui_type")
    if ui_type == "int":
        return "int"
    if ui_type == "float":
        return "float"
    if ui_type == "bool":
        return "bool"
    if ui_type == "date":
        return "date"
    if ui_type == "datetime":
        return "datetime"
    if ui_type == "time":
        return "time"
    if ui_type in {"json", "location"}:
        return "List[Any]" if field.get("json_kind") == "array" else "Dict[str, Any]"
    return "str"


def _inline_item_schema(model: ModelDefinition, *, excluded: set[str]) -> tuple[list[dict], dict]:
    """Build backend and frontend metadata for a one-level nested editor."""
    fields = []
    ui_fields = []
    for field in model.get("fields", []):
        if field["name"] == "id" or field["name"] in excluded:
            continue
        if not ({"c", "u"} & set(field.get("permissions", ""))):
            continue
        item = {
            "name": field["name"],
            "type": _inline_field_type(field),
            "required": bool(field.get("required")),
            "create_optional": bool(field.get("create_optional")),
        }
        fields.append(item)
        if field.get("is_enum"):
            kind = "enum"
        elif field.get("ui_type") in {
            "int",
            "float",
            "bool",
            "datetime",
            "location",
        }:
            kind = field["ui_type"]
        else:
            kind = "any" if field.get("ui_type") == "json" else "str"
        ui_field = {
            "name": field["name"],
            "kind": kind,
            "labelKey": field.get("label_key", field["name"]),
        }
        if field.get("is_enum"):
            ui_field["enumValues"] = field.get("enum_values", [])
        ui_fields.append(ui_field)
    return fields, {"name": model["name"], "fields": ui_fields}


def _normalise_editor(config: dict, *, legacy_editable: Any = None) -> str:
    editor = config.get("editor")
    if editor is None and legacy_editable is not None:
        editor = "select" if legacy_editable else "readonly"
    editor = str(editor or "readonly").lower()
    if editor not in _RELATION_EDITORS:
        console.print(
            f"[yellow]Warning: unsupported relation editor '{editor}'; using readonly.[/yellow]"
        )
        return "readonly"
    return editor


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
            source_search_fields = [
                f for f in source_readable_fields
                if f.get("is_search_field") and f["name"] != fk["name"]
            ]

            reverse_cfg = fk.get("reverse", {}) or {}
            editor = _normalise_editor(reverse_cfg)
            on_remove = str(reverse_cfg.get("on_remove", "delete")).lower()
            if on_remove not in {"delete", "nullify"}:
                console.print(
                    f"[yellow]Warning: {model['name']}.{fk['name']} reverse.on_remove "
                    f"must be delete or nullify; using delete.[/yellow]"
                )
                on_remove = "delete"
            if on_remove == "nullify":
                source_fk_field = next(
                    (field for field in model["fields"] if field["name"] == fk["name"]),
                    None,
                )
                if source_fk_field and not str(source_fk_field.get("type", "")).startswith("Optional["):
                    raise ValueError(
                        f"{model['name']}.{fk['name']} uses reverse.on_remove='nullify' "
                        "but the foreign key is not Optional"
                    )
            inline_fields, inline_schema = _inline_item_schema(
                model, excluded={fk["name"]}
            )

            target_model["reverse_foreign_keys"].append({
                "name": reverse_name,
                "write_name": reverse_name,
                "source_model": model["name"],
                "source_service": model["module_name"],
                "source_module": model["source_module"],
                "source_id_type": model["id_type"],
                "source_fk_field": fk["name"],
                "label_field": model.get("unique_search_field") or model["search_field"],
                "display": editor != "hidden" and fk.get("reverse_display", True),
                "editor": editor,
                "on_remove": on_remove,
                "inline_fields": inline_fields,
                "inline_schema": inline_schema,
                "role_permissions": model.get("role_permissions", {}),
                "actions": model.get("actions", {}),
                "page_edit": model.get("page_edit", False),
                "standalone": model.get("standalone", True),
                "source_readable_fields": source_readable_fields,
                "source_search_fields": source_search_fields,
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
            if isinstance(d, dict)
            and _normalise_editor(d, legacy_editable=d.get("editable", True))
            in {"select", "inline"}
        }

        for d in directions:
            _apply_m2m_direction(d, model, fks, models, model_map, module_map, editable_edges)


def _normalise_io_config(model: ModelDefinition, direction: str) -> dict:
    """Return the model-level import/export config in its canonical shape."""
    raw = (model.get("site_props") or {}).get(f"{direction}able", False)
    if isinstance(raw, dict):
        return raw
    return {} if raw else {"enabled": False}


def _configured_field_names(config: dict) -> tuple[set[str] | None, dict[str, Any]]:
    """Parse the permissive field-list syntax used by import/export configs."""
    raw_fields = config.get("fields")
    if raw_fields is None:
        return None, {}
    names: set[str] = set()
    options: dict[str, Any] = {}
    if isinstance(raw_fields, dict):
        for name, value in raw_fields.items():
            if value is False or value is None:
                continue
            names.add(str(name))
            options[str(name)] = value
    elif isinstance(raw_fields, (list, tuple, set)):
        for value in raw_fields:
            if isinstance(value, str):
                names.add(value)
            elif isinstance(value, dict) and value.get("name"):
                name = str(value["name"])
                names.add(name)
                options[name] = value
    else:
        raise ValueError("importable/exportable 'fields' must be a list or object")
    return names, options


def _relation_mapping(config: dict, *keys: str) -> dict[str, Any]:
    for key in keys:
        value = config.get(key)
        if value is None:
            continue
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, (list, tuple)):
            result = {}
            for item in value:
                if isinstance(item, str):
                    result[item] = True
                elif isinstance(item, dict):
                    name = item.get("name") or item.get("field") or item.get("relation")
                    if name:
                        result[str(name)] = item
            return result
        raise ValueError(f"importable/exportable '{key}' must be a list or object")
    return {}


def _lookup_field(option: Any, default: str) -> tuple[str, str | None]:
    if isinstance(option, str):
        return option, None
    if isinstance(option, dict):
        lookup = option.get("lookup_field") or option.get("field") or option.get("target_field") or default
        column = option.get("column") or option.get("column_name") or option.get("header")
        return str(lookup), str(column) if column else None
    return default, None


def _resolve_import_export_config(
    models: list[ModelDefinition], model_map: dict[str, ModelDefinition]
) -> None:
    """Resolve scalar, FK and explicitly configured M2M CSV columns."""
    system_fields = {"id", "created_at", "updated_at"}
    for model in models:
        fields_by_name = {field["name"]: field for field in model.get("fields", [])}
        fk_by_name = {fk["name"]: fk for fk in model.get("foreign_keys", [])}

        for direction in ("export", "import"):
            config = _normalise_io_config(model, direction)
            selected, field_options = _configured_field_names(config)
            excluded = {str(name) for name in config.get("exclude_fields", [])}
            fk_config = _relation_mapping(config, "foreign_keys", "fk_fields", "fks")

            # A configured FK is also a selected CSV column.
            if selected is not None:
                selected.update(fk_config)

            io_fields = []
            for field in model.get("fields", []):
                name = field["name"]
                permissions = field.get("permissions", "")
                allowed = "r" in permissions if direction == "export" else ("c" in permissions or "u" in permissions)
                if (
                    not allowed
                    or name in system_fields
                    or name in excluded
                    or not field.get(f"{direction}able", True)
                    or (selected is not None and name not in selected)
                ):
                    continue

                entry = {"field": field, "name": name, "column_name": name, "kind": "scalar"}
                if name in fk_by_name:
                    fk = fk_by_name[name]
                    option = fk_config.get(name, field_options.get(name))
                    lookup, column = _lookup_field(option, fk["label_field"])
                    target = model_map.get(fk["target_model"])
                    if target and lookup not in {item["name"] for item in target.get("fields", [])}:
                        raise ValueError(
                            f"{model['name']}.{direction}able foreign key '{name}' "
                            f"references unknown {fk['target_model']} field '{lookup}'"
                        )
                    entry.update({"kind": "fk", "fk": fk, "lookup_field": lookup})
                    if column:
                        entry["column_name"] = column
                io_fields.append(entry)

            # Import upsert cannot work without its matching column. Include it
            # automatically even when an allow-list accidentally omitted it.
            if direction == "import" and model.get("importable") and model.get("import_key"):
                key = model["import_key"]
                if key in fields_by_name and not any(item["name"] == key for item in io_fields):
                    io_fields.insert(0, {
                        "field": fields_by_name[key], "name": key,
                        "column_name": key, "kind": "scalar",
                    })

            raw_m2m = _relation_mapping(config, "m2m", "many_to_many")
            resolved_m2m = []
            for relation_name, option in raw_m2m.items():
                relation = next(
                    (
                        item for item in model.get("m2m_fields", [])
                        if relation_name in {
                            item.get("name"), item.get("write_name"),
                            item.get("target_service"), item.get("target_endpoint"),
                            pluralize(str(item.get("target_service", "")).rsplit("_", 1)[-1]),
                        }
                    ),
                    None,
                )
                if relation is None:
                    raise ValueError(
                        f"{model['name']}.{direction}able m2m relation '{relation_name}' was not found"
                    )
                lookup, column = _lookup_field(option, relation["label_field"])
                target = model_map.get(relation["target_model"])
                if target and lookup not in {item["name"] for item in target.get("fields", [])}:
                    raise ValueError(
                        f"{model['name']}.{direction}able m2m '{relation_name}' "
                        f"references unknown {relation['target_model']} field '{lookup}'"
                    )
                resolved = dict(relation)
                resolved.update({
                    "lookup_field": lookup,
                    "column_name": column or relation_name,
                })
                resolved_m2m.append(resolved)

            model[f"{direction}_fields"] = io_fields
            model[f"{direction}_m2m"] = resolved_m2m


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

    editor = _normalise_editor(d, legacy_editable=d.get("editable", True))
    if editor == "inline" and link_model.get("is_association_table"):
        raise ValueError(
            f"{link_model['name']} cannot use editor='inline' while the link table "
            "has extra association fields"
        )

    # Forward direction: add an editable field to from_model.
    if editor in {"select", "inline"}:
        m2m_field_name = f"{to_model['lower_name']}_ids"
        write_name = pluralize(to_model["module_name"]) if editor == "inline" else m2m_field_name
        inline_fields, inline_schema = _inline_item_schema(to_model, excluded=set())
        existing = next(
            (x for x in from_model.get("m2m_fields", [])
             if x.get("name") == m2m_field_name and x.get("target_model") == to_model["name"]),
            None,
        )
        if existing is None:
            from_model["m2m_fields"].append({
                "name": m2m_field_name,
                "write_name": write_name,
                "editor": editor,
                "on_remove": "unlink",
                "allow_existing": bool(d.get("allow_existing", False)),
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
                "target_id_type": to_model["id_type"],
                "target_role_permissions": to_model.get("role_permissions", {}),
                "inline_fields": inline_fields,
                "inline_schema": inline_schema,
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

        time_column = model.get("timescaledb_time_field")
        if not time_column:
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


def _resolve_property_config_relations(models: list[ModelDefinition]) -> None:
    """For each timeseries model with property_config, build metadata on entity and blueprint."""
    for model in models:
        model.setdefault("property_config_meta", None)
        model.setdefault("reverse_property_config", None)

    for ts_model in models:
        if not ts_model.get("is_timescaledb"):
            continue

        property_config = ts_model.get("property_config")
        if not property_config:
            continue

        entity_field = ts_model.get("timescaledb_entity_field")
        model_table = ts_model.get("timescaledb_model_table")
        if not entity_field or not model_table:
            continue

        # Find the entity model (target of entity_field FK)
        entity_model_name = None
        for fk in ts_model["foreign_keys"]:
            if fk["name"] == entity_field:
                entity_model_name = fk["target_model"]
                break
        if not entity_model_name:
            continue

        entity_model = next((m for m in models if m["name"] == entity_model_name), None)
        if entity_model is None:
            continue

        field_name = property_config.get("field_name", "properties_config")
        config_fields = property_config.get("config_fields", {})
        config_model_name = property_config.get("config_model")
        blueprint_fk = f"{model_table}_id"

        # Resolve config_class and config_fields (config_model takes priority)
        if config_model_name:
            config_class = config_model_name
            if not config_fields:
                # Introspect the user-defined class at runtime
                try:
                    import sys
                    from pydantic_core import PydanticUndefined
                    # Search both entity and timeseries modules
                    candidate_modules = [
                        f"app.models.{entity_model['source_module']}",
                        f"app.models.{ts_model['source_module']}",
                    ]
                    config_cls = None
                    for module_name in candidate_modules:
                        if module_name in sys.modules:
                            module = sys.modules[module_name]
                            config_cls = getattr(module, config_model_name, None)
                            if config_cls is not None:
                                break
                    if config_cls:
                        for fn, fi in config_cls.model_fields.items():
                            if fn == "property_key" or fn.startswith("_"):
                                continue
                            anno = fi.annotation
                            anno_str = anno.__name__ if hasattr(anno, '__name__') else str(anno)
                            if fi.default is not PydanticUndefined and fi.default is not None:
                                config_fields[fn] = f"{anno_str} = {repr(fi.default)}"
                            elif fi.default is not PydanticUndefined:
                                config_fields[fn] = f"Optional[{anno_str}]"
                            else:
                                config_fields[fn] = anno_str
                except Exception:
                    pass
        else:
            config_class = f"{entity_model['name']}PropertyConfig"

        # Find blueprint model
        blueprint_model_name = None
        for fk in entity_model["foreign_keys"]:
            if fk["name"] == blueprint_fk:
                blueprint_model_name = fk["target_model"]
                break
        if not blueprint_model_name:
            # Try pascal case
            from .base import to_pascal
            blueprint_model_name = to_pascal(model_table)

        blueprint_model = next((m for m in models if m["name"] == blueprint_model_name), None)

        # Get field permissions from the injected properties_config field
        field_permissions = "ru"  # default
        for f in entity_model.get("fields", []):
            if f["name"] == field_name:
                field_permissions = f["permissions"]
                break

        # Set property_config_meta on the entity model
        entity_model["property_config_meta"] = {
            "field_name": field_name,
            "config_fields": config_fields,
            "config_class": config_class,
            "field_permissions": field_permissions,
            "blueprint_fk": blueprint_fk,
            "blueprint_model": blueprint_model_name,
            "blueprint_module": model_table,
            "blueprint_properties_field": "properties",
            "ts_model_name": ts_model["name"],
        }

        # Set reverse_property_config on the blueprint model
        if blueprint_model:
            blueprint_model["reverse_property_config"] = {
                "entity_model": entity_model["name"],
                "entity_module": entity_model["module_name"],
                "entity_fk_field": blueprint_fk,
                "properties_field": "properties",
            }


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
    _resolve_property_config_relations(models)
    _resolve_fk_labels_and_reverse(models, model_map)
    _resolve_m2m(models, model_map, module_map)
    _resolve_import_export_config(models, model_map)

    for model in models:
        model["inline_relations"] = [
            {
                "kind": "reverse_fk",
                "write_name": rel["write_name"],
                "target_model": rel["source_model"],
                "role_permissions": rel["role_permissions"],
                "remove_permission": "d" if rel["on_remove"] == "delete" else "u",
            }
            for rel in model.get("reverse_foreign_keys", [])
            if rel.get("editor") == "inline"
        ] + [
            {
                "kind": "m2m",
                "write_name": rel["write_name"],
                "target_model": rel["target_model"],
                "role_permissions": rel["target_role_permissions"],
                "remove_permission": None,
            }
            for rel in model.get("m2m_fields", [])
            if rel.get("editor") == "inline"
        ]

    return models
