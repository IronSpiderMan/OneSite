import keyword
from pathlib import Path
from typing import Any, Dict


class SiteConfigError(ValueError):
    """Raised when ``site_config.json`` exists but cannot be parsed."""


_TOOL_INPUT_TYPE_ALIASES = {
    "str": "str",
    "string": "str",
    "text": "text",
    "number": "number",
    "bool": "bool",
    "boolean": "bool",
    "select": "select",
    "multi_select": "multi_select",
    "list": "multi_select",
    "date": "date",
    "datetime": "datetime",
    "file": "file",
    "files": "files",
    "json": "json",
}
_SCHEDULED_PARAM_TYPE_ALIASES = {
    "str": "str",
    "string": "str",
    "text": "str",
    "select": "str",
    "number": "number",
    "bool": "bool",
    "boolean": "bool",
    "multi_select": "multi_select",
    "list": "multi_select",
    "json": "json",
}
_TOOL_ROLES = {"user", "admin", "developer"}


def validate_tools_config(config: Dict[str, Any]) -> None:
    """Validate and normalize Dashboard tool definitions."""
    tools = config.get("tools")
    if tools is None:
        return
    if not isinstance(tools, list):
        raise SiteConfigError("site_config.json field 'tools' must be a JSON array.")

    seen_tools: set[str] = set()
    seen_handlers: set[str] = set()
    for index, tool in enumerate(tools):
        field = f"site_config.json field 'tools[{index}]'"
        if not isinstance(tool, dict):
            raise SiteConfigError(f"{field} must be a JSON object.")

        name = tool.get("name")
        if (
            not isinstance(name, str)
            or not name.isidentifier()
            or keyword.iskeyword(name)
            or name == "__init__"
        ):
            raise SiteConfigError(f"{field}.name must be a valid Python identifier.")
        if name in seen_tools:
            raise SiteConfigError(f"{field}.name duplicates tool {name!r}.")
        seen_tools.add(name)

        handler = tool.setdefault("handler", name)
        if (
            not isinstance(handler, str)
            or not handler.isidentifier()
            or keyword.iskeyword(handler)
            or handler == "__init__"
        ):
            raise SiteConfigError(f"{field}.handler must be a valid Python identifier.")
        if handler in seen_handlers:
            raise SiteConfigError(f"{field}.handler duplicates handler {handler!r}.")
        seen_handlers.add(handler)

        title = tool.setdefault("title", name.replace("_", " ").title())
        if not isinstance(title, str) or not title.strip():
            raise SiteConfigError(f"{field}.title must be a non-empty string.")
        tool.setdefault("description", "")
        tool.setdefault("placement", "dashboard")
        if tool["placement"] != "dashboard":
            raise SiteConfigError(f"{field}.placement currently only supports 'dashboard'.")

        permissions = tool.setdefault("permissions", ["admin", "developer"])
        if (
            not isinstance(permissions, list)
            or not permissions
            or any(role not in _TOOL_ROLES for role in permissions)
        ):
            raise SiteConfigError(
                f"{field}.permissions must be a non-empty array containing "
                "user, admin, or developer."
            )

        execution = tool.setdefault("execution", {"mode": "background"})
        if not isinstance(execution, dict):
            raise SiteConfigError(f"{field}.execution must be a JSON object.")
        if execution.setdefault("mode", "background") != "background":
            raise SiteConfigError(f"{field}.execution.mode currently only supports 'background'.")
        timeout = execution.setdefault("timeout_seconds", 600)
        if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
            raise SiteConfigError(f"{field}.execution.timeout_seconds must be a positive integer.")

        inputs = tool.setdefault("inputs", [])
        if not isinstance(inputs, list):
            raise SiteConfigError(f"{field}.inputs must be a JSON array.")
        seen_inputs: set[str] = set()
        for input_index, input_config in enumerate(inputs):
            input_field = f"{field}.inputs[{input_index}]"
            if not isinstance(input_config, dict):
                raise SiteConfigError(f"{input_field} must be a JSON object.")
            input_name = input_config.get("name")
            if (
                not isinstance(input_name, str)
                or not input_name.isidentifier()
                or keyword.iskeyword(input_name)
                or input_name == "context"
            ):
                raise SiteConfigError(f"{input_field}.name must be a valid Python identifier.")
            if input_name in seen_inputs:
                raise SiteConfigError(f"{input_field}.name duplicates input {input_name!r}.")
            seen_inputs.add(input_name)

            configured_input_type = input_config.get("type")
            input_type = (
                _TOOL_INPUT_TYPE_ALIASES.get(configured_input_type)
                if isinstance(configured_input_type, str)
                else None
            )
            if input_type is None:
                supported = ", ".join(sorted(_TOOL_INPUT_TYPE_ALIASES))
                raise SiteConfigError(f"{input_field}.type must be one of: {supported}.")
            input_config["type"] = input_type
            input_config.setdefault("label", input_name.replace("_", " ").title())
            input_config.setdefault("required", False)
            if not isinstance(input_config["required"], bool):
                raise SiteConfigError(f"{input_field}.required must be a boolean.")

            if input_type == "number":
                number_kind = input_config.setdefault("number_kind", "float")
                if number_kind not in {"int", "float"}:
                    raise SiteConfigError(f"{input_field}.number_kind must be 'int' or 'float'.")
            if input_type in {"select", "multi_select"}:
                options = input_config.get("options")
                if not isinstance(options, list) or not options:
                    raise SiteConfigError(f"{input_field}.options must be a non-empty array.")
                if any(
                    isinstance(option, dict) and "value" not in option
                    for option in options
                ):
                    raise SiteConfigError(
                        f"{input_field}.options objects must contain a value."
                    )
            if input_type in {"file", "files"}:
                max_size = input_config.setdefault("max_size_mb", 20)
                if isinstance(max_size, bool) or not isinstance(max_size, (int, float)) or max_size <= 0:
                    raise SiteConfigError(f"{input_field}.max_size_mb must be a positive number.")
            if input_type == "files":
                max_files = input_config.setdefault("max_files", 10)
                if isinstance(max_files, bool) or not isinstance(max_files, int) or max_files <= 0:
                    raise SiteConfigError(f"{input_field}.max_files must be a positive integer.")

        result = tool.setdefault("result", {"type": "json"})
        if not isinstance(result, dict) or result.setdefault("type", "json") not in {
            "json", "text", "file", "toast"
        }:
            raise SiteConfigError(
                f"{field}.result.type must be json, text, file, or toast."
            )


def validate_scheduled_tasks_config(config: Dict[str, Any]) -> None:
    """Validate scheduled tasks and normalize legacy schedule/param shapes."""
    tasks = config.get("scheduled_tasks")
    if tasks is None:
        return
    if not isinstance(tasks, list):
        raise SiteConfigError(
            "site_config.json field 'scheduled_tasks' must be a JSON array."
        )

    seen_names: set[str] = set()
    seen_handlers: set[str] = set()
    for index, task in enumerate(tasks):
        field = f"site_config.json field 'scheduled_tasks[{index}]'"
        if not isinstance(task, dict):
            raise SiteConfigError(f"{field} must be a JSON object.")
        name = task.get("name")
        if (
            not isinstance(name, str)
            or not name.isidentifier()
            or keyword.iskeyword(name)
            or name == "__init__"
        ):
            raise SiteConfigError(f"{field}.name must be a valid Python identifier.")
        if name in seen_names:
            raise SiteConfigError(f"{field}.name duplicates task {name!r}.")
        seen_names.add(name)

        handler = task.setdefault("handler", name)
        if (
            not isinstance(handler, str)
            or not handler.isidentifier()
            or keyword.iskeyword(handler)
            or handler == "__init__"
        ):
            raise SiteConfigError(f"{field}.handler must be a valid Python identifier.")
        if handler in seen_handlers:
            raise SiteConfigError(f"{field}.handler duplicates handler {handler!r}.")
        seen_handlers.add(handler)

        task.setdefault("title", name.replace("_", " ").title())
        task.setdefault("description", "")
        task.setdefault("enabled", True)
        if not isinstance(task["enabled"], bool):
            raise SiteConfigError(f"{field}.enabled must be a boolean.")

        schedule = task.get("schedule")
        if schedule is not None:
            if not isinstance(schedule, dict):
                raise SiteConfigError(f"{field}.schedule must be a JSON object.")
            schedule_type = schedule.get("type")
            if schedule_type == "cron":
                cron = schedule.get("cron")
                if not isinstance(cron, str) or len(cron.split()) != 5:
                    raise SiteConfigError(
                        f"{field}.schedule.cron must be a five-part cron expression."
                    )
                task["cron"] = cron
                task["interval"] = 0
            elif schedule_type == "interval":
                seconds = schedule.get("seconds")
                if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds <= 0:
                    raise SiteConfigError(
                        f"{field}.schedule.seconds must be a positive integer."
                    )
                task["cron"] = ""
                task["interval"] = seconds
            else:
                raise SiteConfigError(
                    f"{field}.schedule.type must be 'cron' or 'interval'."
                )
        else:
            interval = task.setdefault("interval", 0)
            if isinstance(interval, bool) or not isinstance(interval, int) or interval < 0:
                raise SiteConfigError(f"{field}.interval must be a non-negative integer.")
            cron = task.setdefault("cron", "")
            if interval == 0 and (not isinstance(cron, str) or len(cron.split()) != 5):
                raise SiteConfigError(
                    f"{field}.cron must be a five-part cron expression when interval is 0."
                )
            task["schedule"] = (
                {"type": "interval", "seconds": interval}
                if interval > 0
                else {"type": "cron", "cron": cron}
            )

        timeout = task.setdefault("timeout_seconds", 600)
        if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
            raise SiteConfigError(f"{field}.timeout_seconds must be a positive integer.")
        if task.setdefault("overlap", "skip") not in {"skip", "queue"}:
            raise SiteConfigError(f"{field}.overlap must be 'skip' or 'queue'.")
        permissions = task.setdefault("manual_permissions", ["admin", "developer"])
        if (
            not isinstance(permissions, list)
            or not permissions
            or any(role not in _TOOL_ROLES for role in permissions)
        ):
            raise SiteConfigError(
                f"{field}.manual_permissions must contain user, admin, or developer."
            )
        notify = task.setdefault(
            "notify",
            {"on_success": False, "on_failure": True, "roles": ["developer"]},
        )
        if not isinstance(notify, dict):
            raise SiteConfigError(f"{field}.notify must be a JSON object.")
        notify.setdefault("on_success", False)
        notify.setdefault("on_failure", True)
        notify.setdefault("roles", ["developer"])
        if not isinstance(notify["on_success"], bool) or not isinstance(
            notify["on_failure"], bool
        ):
            raise SiteConfigError(
                f"{field}.notify success/failure settings must be booleans."
            )
        if not isinstance(notify["roles"], list) or any(
            role not in _TOOL_ROLES for role in notify["roles"]
        ):
            raise SiteConfigError(f"{field}.notify.roles contains an unknown role.")

        raw_params = task.setdefault("params", {})
        if isinstance(raw_params, list):
            normalized_params: dict[str, dict] = {}
            for param_index, param in enumerate(raw_params):
                param_field = f"{field}.params[{param_index}]"
                if not isinstance(param, dict):
                    raise SiteConfigError(f"{param_field} must be a JSON object.")
                param_name = param.get("name")
                if (
                    not isinstance(param_name, str)
                    or not param_name.isidentifier()
                    or keyword.iskeyword(param_name)
                    or param_name == "context"
                ):
                    raise SiteConfigError(f"{param_field}.name must be a valid Python identifier.")
                if param_name in normalized_params:
                    raise SiteConfigError(
                        f"{param_field}.name duplicates parameter {param_name!r}."
                    )
                configured_param_type = param.get("type")
                param_type = (
                    _SCHEDULED_PARAM_TYPE_ALIASES.get(configured_param_type)
                    if isinstance(configured_param_type, str)
                    else None
                )
                if param_type is None:
                    raise SiteConfigError(
                        f"{param_field}.type is not supported for scheduled tasks."
                    )
                default = param.get("default")
                normalized_params[param_name] = {
                    "type": param_type,
                    "default": default,
                    "value": default,
                    "label": param.get("label", param_name.replace("_", " ").title()),
                }
            task["params"] = raw_params = normalized_params
        if not isinstance(raw_params, dict):
            raise SiteConfigError(f"{field}.params must be an object or array.")
        for param_name, param in raw_params.items():
            param_field = f"{field}.params.{param_name}"
            if (
                not isinstance(param_name, str)
                or not param_name.isidentifier()
                or keyword.iskeyword(param_name)
                or param_name == "context"
            ):
                raise SiteConfigError(f"{param_field} must use a valid Python identifier.")
            configured_param_type = param.get("type") if isinstance(param, dict) else None
            param_type = (
                _SCHEDULED_PARAM_TYPE_ALIASES.get(configured_param_type)
                if isinstance(configured_param_type, str)
                else None
            )
            if param_type is None:
                raise SiteConfigError(
                    f"{param_field}.type must be str/string, number, bool/boolean, "
                    "multi_select/list, or json."
                )
            param["type"] = param_type
            param.setdefault("default", None)
            param.setdefault("value", param["default"])
            param.setdefault("label", param_name.replace("_", " ").title())


def validate_mqtt_config(config: Dict[str, Any]) -> None:
    """Validate and normalize the MQTT section used by code generation."""
    mqtt = config.get("mqtt")
    if mqtt is None:
        return
    if not isinstance(mqtt, dict):
        raise SiteConfigError("site_config.json field 'mqtt' must be a JSON object.")

    callbacks = mqtt.get("callbacks", [])
    if not isinstance(callbacks, list):
        raise SiteConfigError(
            "site_config.json field 'mqtt.callbacks' must be a JSON array."
        )

    seen: set[tuple[str, str]] = set()
    for index, callback in enumerate(callbacks):
        field = f"site_config.json field 'mqtt.callbacks[{index}]'"
        if not isinstance(callback, dict):
            raise SiteConfigError(f"{field} must be a JSON object.")

        topic = callback.get("topic")
        if not isinstance(topic, str) or not topic.strip():
            raise SiteConfigError(f"{field}.topic must be a non-empty string.")

        handler = callback.get("handler")
        if (
            not isinstance(handler, str)
            or not handler.isidentifier()
            or keyword.iskeyword(handler)
            or handler == "__init__"
        ):
            raise SiteConfigError(
                f"{field}.handler must be a valid Python identifier."
            )

        qos = callback.setdefault("qos", 1)
        if isinstance(qos, bool) or qos not in (0, 1, 2):
            raise SiteConfigError(f"{field}.qos must be 0, 1, or 2.")

        registration = (topic, handler)
        if registration in seen:
            raise SiteConfigError(
                f"{field} duplicates MQTT callback {topic!r} -> {handler!r}."
            )
        seen.add(registration)


def load_site_config(cwd: Path) -> Dict[str, Any]:
    """Load the project configuration without silently discarding bad input.

    A malformed configuration used to be treated as an empty one.  The next
    sync then wrote default values into ``.env`` and generated a project with
    the wrong settings, which is much harder to recover from than a clear
    error at the configuration boundary.
    """
    config_path = cwd / "site_config.json"
    if config_path.exists():
        import json

        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SiteConfigError(
                f"Unable to parse {config_path}: {exc}"
            ) from exc
        if not isinstance(config, dict):
            raise SiteConfigError(
                f"{config_path} must contain a JSON object at its top level."
            )
        return config
    return {}
