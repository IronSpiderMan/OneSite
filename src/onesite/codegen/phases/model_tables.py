"""Phase 2 — Timeseries model table generation.

Scans model source files for ``is_timescaledb`` configurations and
generates the corresponding model-table definitions, ``_latest`` tables,
and FK-column injections **before** the model-sync and introspection
phases run.
"""

import re
from pathlib import Path
from typing import Any

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


def _scan_ts_configs_new(content: str) -> dict | None:
    """Extract time-series config from new nested ``time_series_table`` dict."""
    m = re.search(
        r"""["']time_series_table["']\s*:\s*\{(.*?)\}""",
        content, re.DOTALL,
    )
    if not m:
        return None
    block = m.group(1)
    return {
        "entity_field": _extract_from_block(block, "entity_field"),
        "metric_field": _extract_from_block(block, "metric_field"),
        "time_field": _extract_from_block(block, "time_field"),
        "model_table": _extract_from_block(block, "model_table"),
    }


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
        filepath.write_text('\n'.join(lines))
        return True
    return False


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
        generate_file(
            "timescaledb_model_table.py.j2",
            {"class_name": class_name, "table_name": table_name},
            models_src_dir / f"{table_name}.py",
        )

        # Inject FK field (e.g. device_model_id) into the entity model source file
        entity_file = models_src_dir / f"{cfg['entity_stem']}.py"
        if entity_file.exists():
            fk_field = f"{table_name}_id"
            if _inject_fk_into_model_source(entity_file, fk_field, table_name):
                console.print(f"[green]Injected {fk_field} into {entity_file.name}[/green]")

    # ── Generate _latest SQLModel (e.g. device_property_history_latest.py) into models/ ──
    for entry in ts_imports:
        ts_cls = entry.get("source_class")
        ts_file = entry.get("source_file")
        ef = entry.get("entity_field")
        es = entry.get("entity_stem")
        mf = entry.get("metric_field")
        if not all([ts_cls, ts_file, ef, es]):
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
            models_src_dir / f"{ts_file}_latest.py",
        )

