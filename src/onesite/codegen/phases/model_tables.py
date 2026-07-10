"""Phase 2 — Timeseries model table generation.

Scans model source files for ``is_timescaledb`` configurations and
generates the corresponding model-table definitions, ``_latest`` tables,
and FK-column injections **before** the model-sync and introspection
phases run.
"""

import re
from pathlib import Path
from typing import Any

from ..file_utils import write_file_with_status
from ..render import generate_file
from .base import console, to_pascal


# ── Source file scanning ──────────────────────────────────────────────────


def _has_ts_config(content: str) -> bool:
    """Check if content has time-series config in new or legacy format."""
    return "time_series_table" in content or "is_timescaledb" in content


def _extract_from_block(block: str, key: str) -> str | None:
    """Extract a quoted string value for *key* from a config dict block."""
    m = re.search(
        rf"""["']{key}["']\s*:\s*["']([^"']+)["']""",
        block,
    )
    return m.group(1) if m else None


def _scan_ts_configs_old(content: str) -> dict | None:
    """Extract time-series config from legacy flat keys."""
    ef = re.search(
        r""""timescaledb_entity_field"\s*:\s*"([^"]+)"|'timescaledb_entity_field'\s*:\s*'([^']+)'""",
        content,
    )
    mf = re.search(
        r""""timescaledb_metric_field"\s*:\s*"([^"]+)"|'timescaledb_metric_field'\s*:\s*'([^']+)'""",
        content,
    )
    mt = re.search(
        r""""timescaledb_model_table"\s*:\s*"([^"]+)"|'timescaledb_model_table'\s*:\s*'([^']+)'"""
        r"""|"timescaledb_device_model"\s*:\s*"([^"]+)"|'timescaledb_device_model'\s*:\s*'([^']+)'""",
        content,
    )
    if not ef and not mt:
        return None
    return {
        "entity_field": ef.group(1) or ef.group(2) if ef else None,
        "metric_field": mf.group(1) or mf.group(2) if mf else None,
        "model_table": mt.group(1) or mt.group(2) or mt.group(3) or mt.group(4) if mt else None,
    }


def _extract_braced_block(text: str, start_pos: int) -> tuple[str, int] | None:
    """Extract a braced block starting at ``start_pos``, handling nesting.

    Returns (block_content, end_pos) or None.
    """
    if start_pos >= len(text) or text[start_pos] != "{":
        return None
    depth = 0
    i = start_pos
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start_pos + 1 : i], i + 1
        i += 1
    return None


def _scan_ts_configs_new(content: str) -> dict | None:
    """Extract time-series config from new nested ``time_series_table`` dict."""
    m = re.search(
        r"""["']time_series_table["']\s*:\s*\{""",
        content,
    )
    if not m:
        return None
    brace_start = m.end() - 1  # position of '{'
    result = _extract_braced_block(content, brace_start)
    if result is None:
        return None
    block, _ = result
    config = {
        "entity_field": _extract_from_block(block, "entity_field"),
        "metric_field": _extract_from_block(block, "metric_field"),
        "time_field": _extract_from_block(block, "time_field"),
        "model_table": _extract_from_block(block, "model_table"),
    }
    # Check for property_config nested block
    pc_match = re.search(
        r"""["']property_config["']\s*:\s*\{""",
        block,
    )
    if pc_match:
        pc_brace_start = pc_match.end() - 1
        pc_result = _extract_braced_block(block, pc_brace_start)
        if pc_result:
            pc_block, _ = pc_result
            field_name = _extract_from_block(pc_block, "field_name") or "properties_config"
            config["property_config"] = True
            config["property_config_field_name"] = field_name
            # Check for config_model (new format: references a user-defined SQLModel class)
            config_model = _extract_from_block(pc_block, "config_model")
            config["property_config_config_model"] = config_model
            # Extract config_fields as a dict (legacy format)
            cf_match = re.search(
                r"""["']config_fields["']\s*:\s*\{""",
                pc_block,
            )
            if cf_match:
                cf_brace_start = cf_match.end() - 1
                cf_result = _extract_braced_block(pc_block, cf_brace_start)
                if cf_result:
                    cf_block, _ = cf_result
                    config["property_config_config_fields"] = dict(
                        re.findall(
                            r"""["'](\w+)["']\s*:\s*["']([^"']+)["']""",
                            cf_block,
                        )
                    )
                else:
                    config["property_config_config_fields"] = {}
            else:
                config["property_config_config_fields"] = {}
        else:
            config["property_config"] = False
            config["property_config_field_name"] = None
            config["property_config_config_model"] = None
            config["property_config_config_fields"] = {}
    else:
        config["property_config"] = False
        config["property_config_field_name"] = None
        config["property_config_config_model"] = None
        config["property_config_config_fields"] = {}
    return config


def _detect_time_column(content: str, ts_config: dict | None = None) -> str:
    """Detect time column: explicit config > auto-detect > 'reported_at'."""
    if ts_config and ts_config.get("time_field"):
        return ts_config["time_field"]
    datetime_fields = re.findall(
        r'^\s*(\w+)\s*:\s*(?:Optional\[)?datetime', content, re.MULTILINE | re.IGNORECASE
    )
    if datetime_fields:
        for cand in ("reported_at", "created_at"):
            if cand in datetime_fields:
                return cand
        return datetime_fields[0]
    return "reported_at"


def _scan_model_table_configs(models_dir: Path) -> tuple[list[dict], list[dict]]:
    """Scan model source text files for time-series config before full introspect.

    Supports both new nested format (``time_series_table`` dict) and legacy flat keys.

    Returns (configs, ts_imports) where:
      configs: for model table generation + FK extensions (files with model_table)
      ts_imports: for ``_latest`` table generation (all time-series files)
    """
    configs: list[dict] = []
    ts_imports: list[dict] = []
    for f in sorted(models_dir.glob("*.py")):
        if f.stem == "__init__":
            continue
        content = f.read_text(encoding="utf-8")
        if not _has_ts_config(content):
            continue

        # Extract class name
        source_class = None
        class_match = re.search(r'class\s+(\w+)\s*\([^)]*\btable=True\b[^)]*\)', content)
        if class_match:
            source_class = class_match.group(1)

        # Try new format first, fall back to legacy
        ts_config = _scan_ts_configs_new(content)
        if ts_config is None:
            ts_config = _scan_ts_configs_old(content)
        if ts_config is None:
            continue

        entity_field = ts_config["entity_field"]
        metric_field = ts_config["metric_field"]
        model_table = ts_config["model_table"]
        time_column = _detect_time_column(content, ts_config)

        # ts_imports: every time-series file (needed for _latest table generation)
        if source_class and entity_field:
            ts_imports.append({
                "source_file": f.stem,
                "source_class": source_class,
                "entity_field": entity_field,
                "entity_stem": entity_field.replace("_id", ""),
                "metric_field": metric_field,
                "time_column": time_column,
            })

        # configs: only files with model_table (needs FK injection + model table gen)
        if model_table and entity_field:
            configs.append({
                "model_table": model_table,
                "entity_field": entity_field,
                "entity_stem": entity_field.replace("_id", ""),
                "metric_field": metric_field,
                "source_file": f.stem,
                "source_class": source_class,
                "property_config": ts_config.get("property_config", False),
                "property_config_field_name": ts_config.get("property_config_field_name"),
                "property_config_config_model": ts_config.get("property_config_config_model"),
                "property_config_config_fields": ts_config.get("property_config_config_fields", {}),
            })

    return configs, ts_imports


def _inject_fk_into_model_source(filepath: Path, fk_field: str, target_table: str) -> bool:
    """Inject FK field (e.g. device_model_id) into model source file if not already present.

    Returns True if injected, False if already present.
    """
    content = filepath.read_text()
    field_decl = f"{fk_field}:"
    if field_decl in content:
        return False

    lines = content.split('\n')
    new_line = f"    {fk_field}: Optional[int] = Field(default=None, foreign_key=\"{target_table}.id\", nullable=True)"

    # Find the last field definition line (indented, has ' = Field(')
    insert_idx = None
    for i, line in enumerate(lines):
        if line[:4] == '    ' and ' = Field(' in line:
            insert_idx = i

    if insert_idx is not None:
        # Ensure Optional is in the typing import
        for i, line in enumerate(lines):
            if line.startswith('from typing import'):
                if 'Optional' not in line:
                    lines[i] = line.replace('from typing import', 'from typing import Optional, ')
                break

        lines.insert(insert_idx, new_line)
        write_file_with_status(filepath, '\n'.join(lines))
        return True
    return False


def _parse_config_class_fields(filepath: Path, class_name: str) -> dict[str, str]:
    """Parse a SQLModel class definition in *filepath* and extract field metadata.

    Returns ``{field_name: type_with_default}`` in the same format as the
    legacy ``config_fields`` dict (e.g. ``{"enabled": "bool = True"}``).
    """
    import ast as _ast

    content = filepath.read_text()
    try:
        tree = _ast.parse(content)
    except SyntaxError:
        return {}

    for node in _ast.walk(tree):
        if not isinstance(node, _ast.ClassDef) or node.name != class_name:
            continue

        fields: dict[str, str] = {}
        for item in node.body:
            if not isinstance(item, _ast.AnnAssign) or not isinstance(item.target, _ast.Name):
                continue

            field_name = item.target.id
            if field_name.startswith("_") or field_name == "property_key":
                continue

            # Resolve type annotation
            anno = _ast.unparse(item.annotation) if hasattr(_ast, "unparse") else _ast.dump(item.annotation)

            # Resolve default value
            default = None
            if item.value is not None:
                try:
                    default = _ast.literal_eval(item.value)
                except (ValueError, TypeError):
                    default = _ast.unparse(item.value) if hasattr(_ast, "unparse") else repr(item.value)

            if default is not None:
                fields[field_name] = f"{anno} = {repr(default)}"
            else:
                fields[field_name] = anno

        return fields

    return {}
    """Convert a config_fields type string to (python_annotation, default_value).

    Examples:
        "Optional[str]"  → ("Optional[str]", "None")
        "str"            → ("str", None)           # required, no default
        "bool = True"    → ("bool", "True")
        "Optional[int]"  → ("Optional[int]", "None")
    """
    ts = type_str.strip()
    default = None
    if "=" in ts:
        ts, default = ts.split("=", 1)
        ts = ts.strip()
        default = default.strip()

    if ts.startswith("Optional["):
        if default is None:
            default = "None"
    return ts, default


def _inject_property_config_into_entity(
    filepath: Path,
    entity_class: str,
    field_name: str,
    config_fields: dict[str, str],
    description: str,
    config_model: str | None = None,
) -> bool:
    """Inject a config model class and typed JSON field into an entity model file.

    When *config_model* is provided (new format), the user has already defined
    the class — only the typed ``list[config_model]`` field is injected.

    When *config_model* is None (legacy format), a ``{Entity}PropertyConfig``
    SQLModel class is generated from *config_fields* and injected alongside
    the typed field.
    """
    content = filepath.read_text()
    if f"{field_name}:" in content:
        return False

    if config_model:
        config_class = config_model
    else:
        config_class = f"{entity_class}PropertyConfig"

    lines = content.split("\n")

    if not config_model:
        # ── Legacy: generate the config model class from config_fields ──
        class_lines = [
            "",
            f"class {config_class}(SQLModel):",
            f'    """Property binding configuration for {entity_class}."""',
            "    property_key: str",
        ]
        for cf_name, cf_type in config_fields.items():
            anno, default = _config_type_to_python(cf_type)
            if default is not None:
                class_lines.append(f"    {cf_name}: {anno} = {default}")
            else:
                class_lines.append(f"    {cf_name}: {anno}")
        class_lines.append("")

        # Find where to insert the model class (before the entity class definition)
        class_def_idx = None
        for i, line in enumerate(lines):
            if f"class {entity_class}(" in line and "table=True" in line:
                class_def_idx = i
                break

        if class_def_idx is None:
            return False

        lines[class_def_idx:class_def_idx] = class_lines

    # ── The field line ──
    field_line = (
        f"    {field_name}: list[{config_class}] = Field("
        f'default=[], sa_column=Column(JSON, info={{"site_props": {{"permissions": "ru"}}}}), '
        f'description="{description}")'
    )

    # Find the entity class definition (may have shifted if legacy class was inserted)
    class_def_idx = None
    for i, line in enumerate(lines):
        if f"class {entity_class}(" in line and "table=True" in line:
            class_def_idx = i
            break

    if class_def_idx is None:
        return False

    # Find the last Field line inside the entity class to insert the field
    insert_idx = None
    for i in range(class_def_idx + 1, len(lines)):
        if lines[i].startswith("    ") and " = Field(" in lines[i]:
            insert_idx = i

    if insert_idx is None:
        return False

    # Ensure needed imports
    for i, line in enumerate(lines):
        if line.startswith("from sqlalchemy import"):
            if "Column" not in line:
                lines[i] = line.replace("from sqlalchemy import", "from sqlalchemy import Column, ")
            if "JSON" not in line:
                lines[i] = lines[i].rstrip() + ", JSON"
        if line.startswith("from typing import"):
            if "Optional" not in line:
                lines[i] = line.replace("from typing import", "from typing import Optional, ")

    lines.insert(insert_idx, field_line)
    write_file_with_status(filepath, "\n".join(lines))
    return True


# ── Public entry point ───────────────────────────────────────────────────


def phase_generate_model_tables(cwd: Path, backend_path: Path) -> None:
    """Generate model table files, ``_latest`` tables, and FK extensions for timeseries configs.

    Generates into ``cwd/models/`` (source) so the files are synced to backend
    by :func:`~onesite.codegen.phases.sync_models.phase_sync_models`.
    Must run before ``phase_sync_models`` and ``phase_introspect``.
    """
    models_src_dir = cwd / "models"
    if not models_src_dir.exists():
        return

    configs, ts_imports = _scan_model_table_configs(models_src_dir)

    # ── Generate model table (e.g. device_model.py) into models/ ──
    for cfg in configs:
        class_name = to_pascal(cfg["model_table"])
        table_name = cfg["model_table"]
        model_table_path = models_src_dir / f"{table_name}.py"

        if model_table_path.exists():
            console.print(f"[dim]Skipped model table {table_name}.py (already exists)[/dim]")
            continue

        generate_file(
            "timescaledb_model_table.py.j2",
            {"class_name": class_name, "table_name": table_name},
            model_table_path,
        )

        # Inject FK field (e.g. device_model_id) into the entity model source file
        entity_file = models_src_dir / f"{cfg['entity_stem']}.py"
        if entity_file.exists():
            fk_field = f"{table_name}_id"
            if _inject_fk_into_model_source(entity_file, fk_field, table_name):
                console.print(f"[green]Injected {fk_field} into {entity_file.name}[/green]")

            # Inject properties_config typed JSON field + config model if property_config is configured
            if cfg.get("property_config"):
                field_name = cfg.get("property_config_field_name", "properties_config")
                entity_class = to_pascal(cfg["entity_stem"])
                config_model = cfg.get("property_config_config_model")
                if config_model:
                    # New format: user-defined class, parse fields from source
                    config_fields = _parse_config_class_fields(entity_file, config_model)
                    if not config_fields:
                        # Try the timeseries source file as well
                        ts_file = models_src_dir / f"{cfg['source_file']}.py"
                        config_fields = _parse_config_class_fields(ts_file, config_model)
                else:
                    # Legacy format: config_fields defined in property_config
                    config_fields = cfg.get("property_config_config_fields", {})
                if _inject_property_config_into_entity(
                    entity_file,
                    entity_class,
                    field_name,
                    config_fields,
                    "Per-property binding configuration",
                    config_model=config_model,
                ):
                    config_cls = config_model or f"{entity_class}PropertyConfig"
                    console.print(
                        f"[green]Injected {config_cls} + {field_name} "
                        f"into {entity_file.name}[/green]"
                    )

    # ── Generate _latest SQLModel (e.g. device_property_history_latest.py) into models/ ──
    for entry in ts_imports:
        ts_cls = entry.get("source_class")
        ts_file = entry.get("source_file")
        ef = entry.get("entity_field")
        es = entry.get("entity_stem")
        mf = entry.get("metric_field")
        if not all([ts_cls, ts_file, ef, es]):
            continue

        latest_path = models_src_dir / f"{ts_file}_latest.py"
        if latest_path.exists():
            continue

        latest_cls = f"{ts_cls}Latest"
        tc = entry.get("time_column", "reported_at")
        generate_file(
            "timescaledb_latest_table.py.j2",
            {
                "ts_cls": ts_cls,
                "latest_cls": latest_cls,
                "ts_file": ts_file,
                "entity_field": ef,
                "entity_table": ef.replace("_id", ""),
                "has_metric": bool(mf),
                "metric_field": mf or "",
                "time_column": tc,
            },
            latest_path,
        )

