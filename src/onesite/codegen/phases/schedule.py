"""Generate the optional built-in Schedule model for a project target."""

from pathlib import Path

from ..render import generate_file


def phase_generate_schedule_model(config: dict, models: list[dict], backend_path: Path, source_path: Path | None = None) -> bool:
    schedule = config.get("schedule") or {}
    if not schedule.get("enabled"):
        return False
    target_name = schedule["target_model"]
    existing = any(model["module_name"] == "schedule" for model in models)
    matches = [model for model in models if model["name"] == target_name]
    if len(matches) != 1:
        raise ValueError(f"schedule.target_model {target_name!r} must name exactly one project model")
    target = matches[0]
    if target["module_name"] == "schedule" or target.get("frontend_only") or target.get("is_link_table"):
        raise ValueError("schedule.target_model must be a regular stored model")
    if target["primary_key_columns"] != ["id"] or target["id_type"] not in ("int", "str"):
        raise ValueError("schedule.target_model must have one int or str primary key named id")
    display = schedule["display_field"]
    if not any(field["name"] == display and "r" in field["permissions"] for field in target["fields"]):
        raise ValueError(f"schedule.display_field {display!r} must be a readable field on {target_name}")
    display_field = next(field for field in target["fields"] if field["name"] == display)
    schedule["role_permissions"] = {
        role: ("r" if role == "user" else "crud")
        if "r" in target.get("role_permissions", {}).get(role, "")
        and "r" in display_field.get("role_permissions", {}).get(role, "")
        else ""
        for role in ("user", "admin", "developer")
    }
    if not any(schedule["role_permissions"].values()):
        raise ValueError("schedule target and display field are unreadable by all roles")
    schedule["target_module"] = target["source_module"]
    schedule["target_table"] = target["table_name"]
    schedule["target_id_type"] = target["id_type"]
    if existing:
        return False  # The project-owned model was already synced and introspected.
    destination = backend_path / "app/models/schedule.py"
    if source_path is not None:
        source = source_path / "models/schedule.py"
        if source.exists():
            return False
        generate_file("schedule_model.py.j2", {"schedule": schedule}, source)
        destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        generate_file("schedule_model.py.j2", {"schedule": schedule}, destination)
    return True
