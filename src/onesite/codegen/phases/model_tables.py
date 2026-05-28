"""Phase 2 — Timeseries model table generation.

Scans model source files for ``is_timescaledb`` configurations and
generates the corresponding model-table definitions, ``_latest`` tables,
and FK-column injections **before** the model-sync and introspection
phases run.
"""

import re
from pathlib import Path
from typing import Any

from .base import console, to_pascal

# ── Inline template for model tables (e.g. device_model.py) ──────────────

_MODEL_TABLE_TPL = '''"""Auto-generated model table for timeseries metric definitions."""
from enum import Enum
from typing import Optional, Annotated
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON
from pydantic.functional_validators import BeforeValidator


def _coerce_empty(v):
    """Convert empty string to None for optional fields."""
    if v == "":
        return None
    return v


CoercedStrList = Annotated[Optional[list[str]], BeforeValidator(_coerce_empty)]
CoercedFloat = Annotated[Optional[float], BeforeValidator(_coerce_empty)]


class {class_name}DataType(str, Enum):
    float = "float"
    int = "int"
    string = "string"
    bool = "bool"
    enum = "enum"


class {class_name}Property(SQLModel):
    """Property definition for {class_name}."""
    key: str = Field(..., description="属性标识符")
    display_name: str = Field(..., description="显示名称")
    unit: Optional[str] = Field(default=None, description="单位")
    data_type: {class_name}DataType = Field(default={class_name}DataType.float, description="数据类型")
    icon: Optional[str] = Field(default=None, description="图标")
    enum_values: CoercedStrList = Field(default=None, description="枚举值列表")
    min_value: CoercedFloat = Field(default=None, description="最小值")
    max_value: CoercedFloat = Field(default=None, description="最大值")


class {class_name}(SQLModel, table=True):
    __tablename__ = "{table_name}"
    __onesite__ = {{
        "permissions": {{"user": "r", "admin": "cru", "developer": "cru"}},
    }}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(..., description="Model name")
    description: str | None = Field(default=None, description="Description")
    properties: list[{class_name}Property] = Field(
        default=[],
        sa_column=Column(JSON),
        description="Metric definitions",
    )
'''


def _generate_latest_model(
    ts_cls: str, latest_cls: str, ts_file: str, entity_field: str, entity_stem: str,
    metric_field: str | None, time_column: str = "reported_at",
) -> str:
    """Generate SQLModel source for a timeseries ``_latest`` table."""
    entity_table = entity_field.replace("_id", "")
    pk_cols = [f'        "{entity_field}"']
    metric_lines = []
    if metric_field:
        metric_lines.append(f"    {metric_field}: str = Field(nullable=False)")
        pk_cols.append(f'        "{metric_field}"')
    pk_joined = ",\n".join(pk_cols)

    return f'''"""Auto-generated latest table for {ts_cls} timeseries data."""
from typing import Any
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Column, DateTime, JSON, PrimaryKeyConstraint


class {latest_cls}(SQLModel, table=True):
    __tablename__ = "{ts_file}_latest"
    __onesite__ = {{
        "is_latest_table": True,
        "permissions": {{"user": "", "admin": "", "developer": ""}},
    }}

    {entity_field}: int = Field(nullable=False, foreign_key="{entity_table}.id")
{chr(10).join(metric_lines)}
    value: Any = Field(sa_column=Column(JSON, nullable=False))
    {time_column}: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    __table_args__ = (
        PrimaryKeyConstraint(
{pk_joined}
        ),
    )
'''


# ── Source file scanning ──────────────────────────────────────────────────


def _scan_model_table_configs(models_dir: Path) -> tuple[list[dict], list[dict]]:
    """Scan model source text files for timescaledb config before full introspect.

    Returns (configs, ts_imports) where:
      configs: for model table generation + FK extensions (files with timescaledb_model_table)
      ts_imports: for importing timeseries models at runtime (all files with is_timescaledb)
    """
    configs: list[dict] = []
    ts_imports: list[dict] = []
    for f in sorted(models_dir.glob("*.py")):
        if f.stem == "__init__":
            continue
        content = f.read_text(encoding="utf-8")
        if "is_timescaledb" not in content:
            continue

        # Common: extract class name, entity_field, metric_field
        source_class = None
        class_match = re.search(r'class\s+(\w+)\s*\([^)]*\btable=True\b[^)]*\)', content)
        if class_match:
            source_class = class_match.group(1)

        entity_field = None
        m_ef = re.search(
            r""""timescaledb_entity_field"\s*:\s*"([^"]+)"|'timescaledb_entity_field'\s*:\s*'([^']+)'""",
            content,
        )
        if m_ef:
            entity_field = m_ef.group(1) or m_ef.group(2)

        metric_field = None
        m_mf = re.search(
            r""""timescaledb_metric_field"\s*:\s*"([^"]+)"|'timescaledb_metric_field'\s*:\s*'([^']+)'""",
            content,
        )
        if m_mf:
            metric_field = m_mf.group(1) or m_mf.group(2)

        # Detect time column: prefer reported_at, then created_at, then first datetime field
        time_column = "reported_at"
        datetime_fields = re.findall(
            r'^\s*(\w+)\s*:\s*(?:Optional\[)?datetime', content, re.MULTILINE | re.IGNORECASE
        )
        if datetime_fields:
            for cand in ("reported_at", "created_at"):
                if cand in datetime_fields:
                    time_column = cand
                    break
            else:
                time_column = datetime_fields[0]

        # Add to ts_imports (every file with is_timescaledb needs runtime import)
        ts_imports.append({
            "source_file": f.stem,
            "source_class": source_class,
            "entity_field": entity_field,
            "entity_stem": entity_field.replace("_id", "") if entity_field else None,
            "metric_field": metric_field,
            "time_column": time_column,
        })

        # Extract timescaledb_model_table (also supports legacy key timescaledb_device_model)
        m = re.search(
            r""""timescaledb_model_table"\s*:\s*"([^"]+)"|'timescaledb_model_table'\s*:\s*'([^']+)'"""
            r"""|"timescaledb_device_model"\s*:\s*"([^"]+)"|'timescaledb_device_model'\s*:\s*'([^']+)'""",
            content,
        )
        if not m:
            continue
        model_table = m.group(1) or m.group(2) or m.group(3) or m.group(4)

        # Skip if no entity_field — can't determine FK target
        if not entity_field:
            continue

        entity_stem = entity_field.replace("_id", "")
        configs.append({
            "model_table": model_table,
            "entity_field": entity_field,
            "entity_stem": entity_stem,
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
    ``_model_extensions.py`` goes directly to ``backend/app/models/`` (runtime helper).
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
        filepath = models_src_dir / f"{table_name}.py"
        filepath.write_text(
            _MODEL_TABLE_TPL.format(class_name=class_name, table_name=table_name)
        )
        console.print(f"[green]Generated model table: {table_name}.py[/green]")

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
        latest_file = models_src_dir / f"{ts_file}_latest.py"
        tc = entry.get("time_column", "reported_at")
        latest_content = _generate_latest_model(ts_cls, latest_cls, ts_file, ef, es, mf, time_column=tc)
        latest_file.write_text(latest_content)
        console.print(f"[green]Generated latest table: {latest_file.name}[/green]")

    # ── Generate ts model imports into backend/app/models/_model_extensions.py ──
    # This ensures SQLModel.metadata knows about timeseries tables at startup.
    backend_models_dir = backend_path / "app" / "models"
    if not backend_models_dir.exists():
        return

    ts_import_lines: list[str] = []
    seen: set[str] = set()
    for entry in configs + ts_imports:
        src = entry["source_file"]
        cls = entry.get("source_class")
        if src not in seen and cls:
            ts_import_lines.append(f"from app.models.{src} import {cls}")
            seen.add(src)

    if ts_import_lines:
        lines = [
            '"""Auto-generated model extensions \u2014 imports timeseries models for table registration."""',
        ]
        lines.extend(ts_import_lines)
        ext_file = backend_models_dir / "_model_extensions.py"
        ext_file.write_text("\n".join(lines) + "\n")
        console.print(f"[green]Generated model extensions: _model_extensions.py[/green]")

        # Append import to __init__.py
        init_file = backend_models_dir / "__init__.py"
        init_content = init_file.read_text() if init_file.exists() else ""
        if "import _model_extensions" not in init_content:
            init_content += "from . import _model_extensions  # noqa: F401\n"
            init_file.write_text(init_content)
