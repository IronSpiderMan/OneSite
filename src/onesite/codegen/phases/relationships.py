"""Phase 4 — Relationship resolution.

Enriches each :class:`~onesite.codegen.types.ModelDefinition` with
resolved foreign-key labels, reverse-FK references, many-to-many
connections via link tables, and timeseries parent-child links.

.. note::

   This phase **mutates** the model dicts in place by adding keys that
   are consumed by the Jinja2 template rendering phases.
"""

import re
from typing import Any

from ..types import ModelDefinition
from .base import ROLE_ORDER, ROLE_TO_ENUM, console, pluralize


_RELATION_EDITORS = {"select", "inline", "embedded", "readonly", "hidden"}


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
        elif field.get("fk_info"):
            kind = "foreign_key"
        elif field.get("ui_type") == "json":
            kind = field.get("json_kind") or "object"
        elif field.get("ui_type") in {
            "int",
            "float",
            "bool",
            "datetime",
            "location",
        }:
            kind = field["ui_type"]
        else:
            kind = "str"
        ui_field = {
            "name": field["name"],
            "kind": kind,
            "labelKey": field.get("label_key", field["name"]),
            "required": bool(field.get("required")),
        }
        if field.get("default") is not None:
            ui_field["default"] = field["default"]
        if field.get("minimum") is not None:
            ui_field["minimum"] = field["minimum"]
        if field.get("maximum") is not None:
            ui_field["maximum"] = field["maximum"]
        if field.get("visible_when") is not None:
            ui_field["visibleWhen"] = field["visible_when"]
        if field.get("required_when") is not None:
            ui_field["requiredWhen"] = field["required_when"]
        if field.get("clear_when_hidden"):
            ui_field["clearWhenHidden"] = True
        if field.get("is_enum"):
            ui_field["enumValues"] = field.get("enum_values", [])
        if field.get("fk_info"):
            # ``foreign_keys`` is the relationship-resolution source of truth:
            # its target model, service, and label have already been resolved
            # against the generated model set.  The field-level copy is still
            # useful as a marker, but can retain the pre-resolution values.
            fk = next(
                (item for item in model.get("foreign_keys", []) if item["name"] == field["name"]),
                field["fk_info"],
            )
            ui_field["foreignKey"] = {
                "targetModel": fk["target_model"],
                "targetService": fk["target_service"],
                "labelField": fk["label_field"],
            }
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
            fk["target_id_type"] = target_model["id_type"]

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
            inline_layout = str(reverse_cfg.get("layout", "cards")).lower()
            if inline_layout not in {"cards", "table"}:
                console.print(
                    f"[yellow]Warning: {model['name']}.{fk['name']} reverse.layout "
                    f"must be cards or table; using cards.[/yellow]"
                )
                inline_layout = "cards"
            allow_existing = bool(reverse_cfg.get("allow_existing", editor == "embedded"))
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
                "inline_layout": inline_layout,
                "allow_existing": allow_existing,
                "on_remove": on_remove,
                "inline_fields": inline_fields,
                "inline_schema": inline_schema,
                "role_permissions": model.get("role_permissions", {}),
                "actions": model.get("actions", {}),
                "has_dynamic_action_states": model.get("has_dynamic_action_states", False),
                "page_edit": model.get("page_edit", False),
                "edit_mode": model.get("edit_mode", "modal"),
                "standalone": model.get("standalone", True),
                "source_readable_fields": source_readable_fields,
                "source_search_fields": source_search_fields,
            })

    # A source model can have more than one FK.  While processing its first
    # reverse relation, later FKs have not necessarily had their labels and
    # services resolved yet.  Rebuild the inline schemas now that every FK is
    # resolved so their dropdown loader metadata is always canonical.
    for target_model in models:
        for relation in target_model.get("reverse_foreign_keys", []):
            source_model = model_map[relation["source_model"]]
            inline_fields, inline_schema = _inline_item_schema(
                source_model, excluded={relation["source_fk_field"]}
            )
            relation["inline_fields"] = inline_fields
            relation["inline_schema"] = inline_schema

    # Report filters use the same resolved relationship metadata as list-page
    # filters.  Introspection happens before relationship resolution, so refresh
    # the initially inferred target service and label field here.
    for model in models:
        report = model.get("reports") or {}
        report_filters = report.get("filters", [])
        for item in report_filters:
            if not item.get("is_foreign_key"):
                continue
            fk = next(
                (candidate for candidate in model.get("foreign_keys", []) if candidate["name"] == item["field"]),
                None,
            )
            if fk is not None:
                item["foreign_key"] = {
                    "target_model": fk["target_model"],
                    "target_service": fk["target_service"],
                    "label_field": fk["label_field"],
                }


def _resolve_tree_view_leaves(models: list[ModelDefinition]) -> None:
    """Resolve an optional second model rendered as terminal tree-page nodes."""

    lookup = {
        key.lower(): value
        for model in models
        for key, value in (
            (model["name"], model),
            (model["module_name"], model),
            (model.get("table_name", ""), model),
        )
        if key
    }
    for model in models:
        model["tree_leaf"] = None
        tree_config = model.get("site_props", {}).get("tree_view", "auto")
        if not model.get("is_tree") or not isinstance(tree_config, dict):
            continue
        raw_leaf = tree_config.get("leaf") or tree_config.get("leaf_model")
        if raw_leaf is None:
            continue
        leaf_config = {"model": raw_leaf} if isinstance(raw_leaf, str) else raw_leaf
        if not isinstance(leaf_config, dict) or not leaf_config.get("model"):
            raise ValueError(
                f"{model['name']} tree_view.leaf must be a model name or configuration object"
            )
        leaf_model = lookup.get(str(leaf_config["model"]).lower())
        if leaf_model is None:
            raise ValueError(
                f"{model['name']} tree_view leaf references unknown model "
                f"'{leaf_config['model']}'"
            )
        parent_field = leaf_config.get("parent_field")
        candidates = [
            fk
            for fk in leaf_model.get("foreign_keys", [])
            if fk.get("target_model") == model["name"]
            and (parent_field is None or fk.get("name") == parent_field)
        ]
        if len(candidates) != 1:
            detail = f" using parent_field='{parent_field}'" if parent_field else ""
            raise ValueError(
                f"{model['name']} tree_view leaf model {leaf_model['name']} must have "
                f"exactly one direct foreign key to {model['name']}{detail}"
            )
        relation = candidates[0]
        label_field = leaf_config.get("label_field") or leaf_model.get(
            "unique_search_field"
        ) or leaf_model["search_field"]
        if not any(field["name"] == label_field for field in leaf_model.get("fields", [])):
            raise ValueError(
                f"{model['name']} tree_view leaf label_field '{label_field}' does not exist "
                f"on {leaf_model['name']}"
            )
        page_size = leaf_config.get("page_size", 20)
        if isinstance(page_size, bool) or not isinstance(page_size, int) or page_size < 1:
            raise ValueError(
                f"{model['name']} tree_view leaf page_size must be a positive integer"
            )
        model["tree_leaf"] = {
            "model": leaf_model["name"],
            "service": leaf_model["module_name"],
            "parent_field": relation["name"],
            "label_field": label_field,
            "id_type": leaf_model["id_type"],
            "role_permissions": leaf_model.get("role_permissions", {}),
            "standalone": leaf_model.get("standalone", True),
            "page_size": page_size,
        }


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


def _csv_header_labels(
    model: ModelDefinition, field_name: str, default: str, field: dict | None = None
) -> dict[str, str]:
    """Resolve the localized CSV headers for a generated export column.

    This deliberately follows the same precedence as generated frontend labels:
    field-level ``translations`` win, followed by the model-level
    ``translations.<language>.fields.<field>`` entry.  A field name remains the
    fallback so existing exports without translations retain their headers.
    """
    labels = {"en": default, "zh": default}
    model_translations = model.get("translations", {})
    if not isinstance(model_translations, dict):
        model_translations = {}

    for language in labels:
        model_pack = model_translations.get(language)
        if isinstance(model_pack, dict):
            translated_fields = model_pack.get("fields")
            translated = (
                translated_fields.get(field_name)
                if isinstance(translated_fields, dict)
                else None
            )
            if isinstance(translated, str) and translated:
                labels[language] = translated

        if field:
            field_translations = field.get("translations", {})
            translated = (
                field_translations.get(language)
                if isinstance(field_translations, dict)
                else None
            )
            if isinstance(translated, str) and translated:
                labels[language] = translated

    return labels


def _resolve_import_export_config(
    models: list[ModelDefinition], model_map: dict[str, ModelDefinition]
) -> None:
    """Resolve scalar, FK, M2M and reverse-FK CSV columns.

    Reverse one-to-many columns are export-only and use the source model's
    reverse relation name.  For example, ``{"reverse_foreign_keys":
    {"orders": "number"}}`` exports each parent row's related order numbers
    as one semicolon-delimited ``orders`` column.
    """
    system_fields = {"id", "created_at", "updated_at"}
    for model in models:
        fields_by_name = {field["name"]: field for field in model.get("fields", [])}
        fk_by_name = {fk["name"]: fk for fk in model.get("foreign_keys", [])}

        for direction in ("export", "import"):
            config = _normalise_io_config(model, direction)
            custom = config.get("custom", False)
            if not isinstance(custom, bool):
                raise ValueError(
                    f"{model['name']}.{direction}able 'custom' must be a boolean"
                )
            model[f"custom_{direction}able"] = custom
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

                entry = {
                    "field": field,
                    "name": name,
                    "column_name": name,
                    "kind": "scalar",
                }
                has_custom_column_name = False
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
                        has_custom_column_name = True
                if direction == "export":
                    # An explicitly configured CSV column header is intentional;
                    # otherwise, select its title from the active UI language.
                    entry["header_labels"] = (
                        {"en": entry["column_name"], "zh": entry["column_name"]}
                        if has_custom_column_name
                        else _csv_header_labels(model, name, entry["column_name"], field)
                    )
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
                if direction == "export":
                    resolved["header_labels"] = (
                        {"en": column, "zh": column}
                        if column
                        else _csv_header_labels(model, relation_name, relation_name)
                    )
                resolved_m2m.append(resolved)

            resolved_reverse_fks = []
            if direction == "export":
                raw_reverse_fks = _relation_mapping(
                    config,
                    "reverse_foreign_keys",
                    "reverse_fks",
                    "reverse_fk",
                )
                for relation_name, option in raw_reverse_fks.items():
                    relation = next(
                        (
                            item
                            for item in model.get("reverse_foreign_keys", [])
                            if relation_name
                            in {
                                item.get("name"),
                                item.get("write_name"),
                                item.get("source_service"),
                                pluralize(str(item.get("source_service", "")).rsplit("_", 1)[-1]),
                            }
                        ),
                        None,
                    )
                    if relation is None:
                        raise ValueError(
                            f"{model['name']}.exportable reverse foreign key "
                            f"'{relation_name}' was not found"
                        )

                    lookup, column = _lookup_field(option, relation["label_field"])
                    source = model_map.get(relation["source_model"])
                    if source and lookup not in {item["name"] for item in source.get("fields", [])}:
                        raise ValueError(
                            f"{model['name']}.exportable reverse foreign key "
                            f"'{relation_name}' references unknown "
                            f"{relation['source_model']} field '{lookup}'"
                        )

                    resolved = dict(relation)
                    resolved.update(
                        {
                            "lookup_field": lookup,
                            "column_name": column or relation_name,
                            "header_labels": (
                                {"en": column, "zh": column}
                                if column
                                else _csv_header_labels(model, relation_name, relation_name)
                            ),
                            "value_cache_name": (
                                f"reverse_{relation['source_service']}_"
                                f"{relation['source_fk_field']}_values"
                            ),
                        }
                    )
                    resolved_reverse_fks.append(resolved)

            model[f"{direction}_fields"] = io_fields
            model[f"{direction}_m2m"] = resolved_m2m
            if direction == "export":
                model["export_reverse_fks"] = resolved_reverse_fks


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
        raw_timeseries = model.get("site_props", {}).get("time_series_table") or {}
        latest_table = raw_timeseries.get("latest_table") or f"{model['table_name']}_latest"
        if not isinstance(latest_table, str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*", latest_table
        ):
            raise ValueError(
                f"{model['name']} time_series_table.latest_table must be a valid "
                "SQL identifier"
            )
        model["timescaledb_latest_table_name"] = latest_table

        for metadata_name in (
            "metric_label_field",
            "metric_data_type_field",
            "metric_unit_field",
        ):
            value = raw_timeseries.get(metadata_name)
            if value is not None and (
                not isinstance(value, str)
                or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value)
            ):
                raise ValueError(
                    f"{model['name']} time_series_table.{metadata_name} "
                    "must be a valid field name"
                )
            model[f"timescaledb_{metadata_name}"] = value

        metric_field = model.get("timescaledb_metric_field")
        metric_target_table = raw_timeseries.get("metric_target_table")
        metric_target_field = raw_timeseries.get("metric_target_field", "id")
        for key, value in (
            ("metric_target_table", metric_target_table),
            ("metric_target_field", metric_target_field),
        ):
            if value is not None and (
                not isinstance(value, str)
                or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value)
            ):
                raise ValueError(
                    f"{model['name']} time_series_table.{key} must be a valid SQL identifier"
                )
        metric_fk = next(
            (
                fk
                for fk in model.get("foreign_keys", [])
                if fk["name"] == metric_field
            ),
            None,
        )
        model["timescaledb_metric_target_table"] = metric_target_table or (
            metric_fk.get("target_service") if metric_fk else None
        )
        model["timescaledb_metric_target_field"] = metric_target_field

        raw_policy = raw_timeseries.get("lifecycle", {})
        if raw_policy and not isinstance(raw_policy, dict):
            raise ValueError(
                f"{model['name']} time_series_table.lifecycle must be an object"
            )

        def _interval(name: str, default: str | None = None) -> str | None:
            value = raw_policy.get(name, default)
            if value is None:
                return None
            if not isinstance(value, str) or not re.fullmatch(
                r"[1-9][0-9]*\s+(second|minute|hour|day|week|month|year)s?", value
            ):
                raise ValueError(
                    f"{model['name']} time_series_table.lifecycle.{name} "
                    "must be a positive PostgreSQL interval such as '7 days'"
                )
            return value

        continuous = bool(raw_policy.get("continuous_aggregate", False))
        model["timescaledb_lifecycle"] = {
            "chunk_interval": _interval("chunk_interval"),
            "compress_after": _interval("compress_after"),
            "retention_after": _interval("retention_after"),
            "bucket_interval": _interval("bucket_interval", "1 hour") if continuous else None,
            "refresh_start_offset": _interval("refresh_start_offset"),
            "refresh_end_offset": _interval("refresh_end_offset", "1 hour") if continuous else None,
            "refresh_schedule_interval": _interval(
                "refresh_schedule_interval", "1 hour"
            ) if continuous else None,
        }
        model["timescaledb_continuous_aggregate_name"] = f"{model['table_name']}_hourly"

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

def _resolve_definition_bindings(models: list[ModelDefinition]) -> None:
    """Resolve entity-owned definition bindings independently of timeseries."""
    for model in models:
        model["definition_binding_meta"] = None
        model["reverse_definition_bindings"] = []

    model_by_name = {model["name"]: model for model in models}
    for entity_model in models:
        binding = entity_model.get("definition_binding")
        if not binding:
            continue

        definition_fk = binding["definition_fk"]
        definitions_field = binding["definitions_field"]
        config_field = binding.get("instance_config_field")

        fk = next(
            (item for item in entity_model["foreign_keys"] if item["name"] == definition_fk),
            None,
        )
        if fk is None:
            raise ValueError(
                f"{entity_model['name']} definition_binding.definition_fk "
                f"references non-FK field {definition_fk!r}"
            )

        definition_model = model_by_name.get(fk["target_model"])
        if definition_model is None:
            raise ValueError(
                f"{entity_model['name']} definition binding target "
                f"{fk['target_model']!r} was not introspected"
            )
        if not any(field["name"] == definitions_field for field in definition_model["fields"]):
            raise ValueError(
                f"{definition_model['name']} has no definitions field {definitions_field!r}"
            )

        config_class = None
        config_permissions = ""
        if config_field:
            field = next(
                (item for item in entity_model["fields"] if item["name"] == config_field),
                None,
            )
            if field is None:
                raise ValueError(
                    f"{entity_model['name']} has no instance config field {config_field!r}"
                )
            schema = field.get("json_item_schema") or {}
            config_class = schema.get("name")
            if not config_class:
                raise ValueError(
                    f"{entity_model['name']}.{config_field} must be typed as "
                    "dict[str, SQLModel]"
                )
            config_permissions = field["permissions"]

        entity_model["definition_binding_meta"] = {
            "definition_fk": definition_fk,
            "definition_model": definition_model["name"],
            "definition_module": definition_model["source_module"],
            "definitions_field": definitions_field,
            "config_field": config_field,
            "config_class": config_class,
            "config_permissions": config_permissions,
            "key_policy": binding.get("key_policy", "definition"),
            "on_definition_change": binding.get("on_definition_change", "reset"),
            "protect_definitions_when_used": binding.get(
                "protect_definitions_when_used", True
            ),
        }
        definition_model["reverse_definition_bindings"].append({
            "entity_model": entity_model["name"],
            "entity_module": entity_model["source_module"],
            "entity_fk_field": definition_fk,
            "definitions_field": definitions_field,
            "protect_definitions_when_used": binding.get(
                "protect_definitions_when_used", True
            ),
        })


def _resolve_dict_key_references(models: list[ModelDefinition]) -> None:
    """Resolve logical references to keys of FK-owned JSON dictionaries."""
    for model in models:
        model["dict_key_reference_meta"] = []
        model["reverse_dict_key_references"] = []
        for field in model.get("fields", []):
            field["dict_key_reference"] = None

    model_by_name = {model["name"]: model for model in models}
    for model in models:
        raw_references = model.get("dict_key_references") or {}
        if not isinstance(raw_references, dict):
            raise ValueError(
                f"{model['name']} dict_key_references must be an object"
            )

        fields_by_name = {field["name"]: field for field in model["fields"]}
        fks_by_name = {fk["name"]: fk for fk in model["foreign_keys"]}
        for reference_field_name, raw_config in raw_references.items():
            if hasattr(raw_config, "model_dump"):
                raw_config = raw_config.model_dump(mode="python")
            if not isinstance(raw_config, dict):
                raise ValueError(
                    f"{model['name']}.dict_key_references.{reference_field_name} "
                    "must be an object"
                )

            reference_field = fields_by_name.get(reference_field_name)
            if reference_field is None:
                raise ValueError(
                    f"{model['name']} dict_key_references references unknown field "
                    f"{reference_field_name!r}"
                )
            if reference_field.get("type") not in {"str", "Optional[str]"}:
                raise ValueError(
                    f"{model['name']}.{reference_field_name} must be a string field"
                )

            owner_fk_name = raw_config.get("owner_fk")
            owner_fk = fks_by_name.get(owner_fk_name)
            if owner_fk is None:
                raise ValueError(
                    f"{model['name']}.{reference_field_name} owner_fk "
                    f"{owner_fk_name!r} must be a foreign key field"
                )

            owner_model = model_by_name.get(owner_fk["target_model"])
            if owner_model is None:
                raise ValueError(
                    f"{model['name']}.{reference_field_name} owner target "
                    f"{owner_fk['target_model']!r} was not introspected"
                )

            source_field_name = raw_config.get("source_field")
            source_field = next(
                (
                    field
                    for field in owner_model["fields"]
                    if field["name"] == source_field_name
                ),
                None,
            )
            if source_field is None:
                raise ValueError(
                    f"{owner_model['name']} has no source field "
                    f"{source_field_name!r}"
                )
            if (
                source_field.get("json_kind") != "object"
                or not source_field.get("json_item_schema")
            ):
                raise ValueError(
                    f"{owner_model['name']}.{source_field_name} must be typed as "
                    "dict[str, SQLModel]"
                )

            item_schema = source_field["json_item_schema"]
            display_field = raw_config.get("display_field")
            item_field_names = {
                item.get("name") for item in item_schema.get("fields", [])
            }
            if display_field is not None and display_field not in item_field_names:
                raise ValueError(
                    f"{model['name']}.{reference_field_name} display_field "
                    f"{display_field!r} does not exist on {item_schema.get('name')}"
                )
            if raw_config.get("on_source_change", "restrict") != "restrict":
                raise ValueError(
                    f"{model['name']}.{reference_field_name} only supports "
                    "on_source_change='restrict'"
                )

            meta = {
                "field": reference_field_name,
                "owner_fk": owner_fk_name,
                "owner_model": owner_model["name"],
                "owner_module": owner_model["source_module"],
                "owner_id_type": owner_model["id_type"],
                "owner_field": owner_model.get("owner_field"),
                "source_field": source_field_name,
                "value_model": item_schema.get("name"),
                "display_field": display_field,
                "on_source_change": "restrict",
            }
            model["dict_key_reference_meta"].append(meta)
            reference_field["dict_key_reference"] = meta
            owner_model["reverse_dict_key_references"].append({
                "source_model": model["name"],
                "source_module": model["source_module"],
                "owner_fk": owner_fk_name,
                "reference_field": reference_field_name,
                "source_field": source_field_name,
                "on_source_change": "restrict",
            })


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
                ts_model["timescaledb_entity_source_module"] = model["source_module"]
                ts_model["timescaledb_entity_label_field"] = model.get("search_field") or "id"
                ts_model["timescaledb_entity_id_field"] = "id"
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
                    "metric_label_field": ts_model.get("timescaledb_metric_label_field"),
                    "metric_data_type_field": ts_model.get("timescaledb_metric_data_type_field"),
                    "metric_unit_field": ts_model.get("timescaledb_metric_unit_field"),
                    "time_field": ts_model.get("timescaledb_time_column", "created_at"),
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
    _resolve_definition_bindings(models)
    _resolve_dict_key_references(models)
    _resolve_fk_labels_and_reverse(models, model_map)
    _resolve_tree_view_leaves(models)
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

    # An embedded reverse-FK editor renders the child model's normal list and
    # modal CRUD UI inside its parent's detail tab.  The child has no route of
    # its own when ``standalone`` is false, but still needs a generated store
    # and reusable list component.
    embedded_sources = {
        rel["source_model"]
        for parent in models
        for rel in parent.get("reverse_foreign_keys", [])
        if rel.get("editor") == "embedded"
    }
    for model in models:
        model["has_embedded_page"] = model["name"] in embedded_sources
        model["has_embedded_reverse"] = any(
            rel.get("editor") == "embedded"
            for rel in model.get("reverse_foreign_keys", [])
        )

    return models
