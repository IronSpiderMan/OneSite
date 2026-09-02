"""Generate storage artifacts for time-series models.

Time-series configuration deliberately owns storage concerns only. Definition
models, foreign keys, and per-item configuration fields are authored on their
entity models and are never generated from a time-series declaration.
"""

import re
from pathlib import Path

from ..render import generate_file
from ...project_paths import get_project_paths


def _extract_block(text: str, start: int, opening: str, closing: str) -> str | None:
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[start + 1:index]
    return None


def _time_series_block(content: str) -> str | None:
    """Return the body of dict or typed ``time_series_table`` declarations."""
    patterns = (
        (r"[\"']time_series_table[\"']\s*:\s*\{", "{", "}"),
        (r"time_series_table\s*=\s*TimeSeriesTableConfig\s*\(", "(", ")"),
    )
    for pattern, opening, closing in patterns:
        match = re.search(pattern, content)
        if match:
            return _extract_block(content, match.end() - 1, opening, closing)
    return None


def _string_option(block: str, name: str) -> str | None:
    match = re.search(
        rf"(?:[\"']{name}[\"']\s*:\s*|\b{name}\s*=\s*)[\"']([^\"']+)[\"']",
        block,
    )
    return match.group(1) if match else None


def _detect_time_column(content: str, configured: str | None) -> str:
    if configured:
        return configured
    datetime_fields = re.findall(
        r"^\s*(\w+)\s*:\s*(?:Optional\[)?datetime",
        content,
        re.MULTILINE | re.IGNORECASE,
    )
    for candidate in ("reported_at", "created_at"):
        if candidate in datetime_fields:
            return candidate
    return datetime_fields[0] if datetime_fields else "reported_at"


def _scan_timeseries(models_dir: Path) -> list[dict[str, str | None]]:
    entries: list[dict[str, str | None]] = []
    for path in sorted(models_dir.glob("*.py")):
        if path.stem == "__init__":
            continue
        content = path.read_text(encoding="utf-8")
        block = _time_series_block(content)
        if block is None:
            continue
        class_match = re.search(
            r"class\s+(\w+)\s*\([^)]*\btable=True\b[^)]*\)", content
        )
        entity_field = _string_option(block, "entity_field")
        if not class_match or not entity_field:
            continue
        entries.append({
            "source_file": path.stem,
            "source_class": class_match.group(1),
            "entity_field": entity_field,
            "entity_stem": entity_field.removesuffix("_id"),
            "metric_field": _string_option(block, "metric_field"),
            "latest_table": _string_option(block, "latest_table"),
            "time_column": _detect_time_column(
                content, _string_option(block, "time_field")
            ),
        })
    return entries


def phase_generate_timeseries_artifacts(cwd: Path, backend_path: Path) -> None:
    """Generate only the ``_latest`` model required by time-series storage."""
    del backend_path  # Artifacts are authored in models/ and synced next.
    models_src_dir = get_project_paths(cwd).models
    if not models_src_dir.exists():
        return

    for entry in _scan_timeseries(models_src_dir):
        ts_cls = entry["source_class"]
        ts_file = entry["source_file"]
        entity_field = entry["entity_field"]
        entity_stem = entry["entity_stem"]
        metric_field = entry["metric_field"]
        latest_table = entry["latest_table"] or f"{ts_file}_latest"
        if not all((ts_cls, ts_file, entity_field, entity_stem)):
            continue

        latest_path = models_src_dir / f"{ts_file}_latest.py"
        if latest_path.exists():
            continue

        generate_file(
            "timescaledb_latest_table.py.j2",
            {
                "ts_cls": ts_cls,
                "latest_cls": f"{ts_cls}Latest",
                "ts_file": ts_file,
                "entity_field": entity_field,
                "entity_table": entity_stem,
                "has_metric": bool(metric_field),
                "metric_field": metric_field or "",
                "latest_table": latest_table,
                "time_column": entry["time_column"],
            },
            latest_path,
        )
