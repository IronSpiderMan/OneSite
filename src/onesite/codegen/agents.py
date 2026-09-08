"""Compile optional built-in agents and mirror their developer-owned extensions."""

import ast
import json
import keyword
import re
from pathlib import Path
from urllib.parse import urlparse

from pydantic import ValidationError

from ..config import AgentConfig
from ..project_paths import get_project_paths
from .config import SiteConfigError
from .file_utils import copy_file_with_status
from .render import generate_file

HOOKS = {"before_run", "before_model", "before_tool", "after_tool", "after_run", "on_error"}
OPERATIONS = {"list", "get", "create", "update", "delete", "bulk_delete", "import"}
OPERATION_ALIASES = {"c": ["create"], "r": ["list", "get"], "u": ["update"], "d": ["delete"]}
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def expand_operation(operation: str) -> list[str]:
    if operation and set(operation) <= set("crud"):
        return [name for char in operation for name in OPERATION_ALIASES[char]]
    return [operation]


def validate_agents_config(config: dict) -> None:
    agents = config.setdefault("agents", {})
    if not isinstance(agents, dict):
        raise SiteConfigError("agents must be an object")
    for key, value in agents.items():
        if not isinstance(key, str) or not IDENTIFIER.fullmatch(key):
            raise SiteConfigError("agents keys must be Python identifiers")
        try:
            definition = AgentConfig.model_validate(value).model_dump()
        except ValidationError as exc:
            raise SiteConfigError(f"agents.{key}: {exc}") from exc
        for field in ("model", "title", "api_key_env"):
            if not definition[field].strip():
                raise SiteConfigError(f"agents.{key}.{field} must not be empty")
        parsed = urlparse(definition["base_url"])
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username:
            raise SiteConfigError(
                f"agents.{key}.base_url must be an HTTP(S) URL without credentials"
            )
        if not definition["roles"]:
            raise SiteConfigError(f"agents.{key}.roles must not be empty")
        for model, operations in definition["model_tools"].items():
            if not IDENTIFIER.fullmatch(model):
                raise SiteConfigError(f"Invalid agent model name: {model}")
            expanded = []
            for operation in operations:
                names = expand_operation(operation)
                if set(names) - OPERATIONS:
                    raise SiteConfigError(f"Unknown agent operation: {model}.{operation}")
                expanded.extend(names)
            definition["model_tools"][model] = list(dict.fromkeys(expanded))
        for name in definition["custom_tools"]:
            if not IDENTIFIER.fullmatch(name) or name in {"__init__", "request_input"} or keyword.iskeyword(name):
                raise SiteConfigError(f"Invalid custom agent tool: {name}")
        if len(set(definition["custom_tools"])) != len(definition["custom_tools"]):
            raise SiteConfigError("Duplicate custom agent tool")
        confirmation = definition["require_confirmation"]
        if isinstance(confirmation, list):
            tool_names = set(definition["custom_tools"]) | {
                f"{model}_{op}" for model, ops in definition["model_tools"].items() for op in ops
            }
            expanded = []
            for name in confirmation:
                names = [name] if name in tool_names else expand_operation(name)
                if set(names) - OPERATIONS - tool_names:
                    raise SiteConfigError(f"agents.{key}: Unknown confirmation operation or tool: {name}")
                expanded.extend(names)
            definition["require_confirmation"] = list(dict.fromkeys(expanded))
        for hook, handler in definition["hooks"].items():
            if hook not in HOOKS or not re.fullmatch(
                r"agent_hooks\.[A-Za-z_][A-Za-z0-9_]*", handler
            ):
                raise SiteConfigError(f"Invalid agent hook: {hook}={handler}")
        agents[key] = definition


def _validate_function(path: Path, name: str) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    if not any(isinstance(node, ast.AsyncFunctionDef) and node.name == name for node in tree.body):
        raise SiteConfigError(f"{path} must declare async def {name}")


def generate_agents(config: dict, models: list, cwd: Path, backend: Path) -> None:
    agents = config.get("agents", {})
    paths = get_project_paths(cwd)
    outputs = {
        "agent_runtime.py.j2": backend / "app/core/agent.py",
        "agent_tools.py.j2": backend / "app/core/agent_tools.py",
        "agent_models.py.j2": backend / "app/core/agent_models.py",
        "agents_api.py.j2": backend / "app/api/endpoints/agents.py",
        "agent_page.tsx.j2": paths.frontend / "src/pages/Agent.tsx",
    }
    if not agents:
        for path in outputs.values():
            path.unlink(missing_ok=True)
        return
    for model in models:
        if (
            model.get("table_name") in {"agent_session", "agent_message"}
            or model["module_name"] == "agents"
        ):
            raise SiteConfigError(
                "AgentSession, AgentMessage and the agents API module are reserved when agents are enabled"
            )
    lookup = {model["name"]: model for model in models}
    metadata = {}
    for key, agent in agents.items():
        names = set(agent["custom_tools"])
        for model_name, operations in agent["model_tools"].items():
            model = lookup.get(model_name)
            if model is None or any(
                model.get(flag)
                for flag in (
                    "is_singleton",
                    "is_timescaledb",
                    "is_notification_table",
                    "is_latest_table",
                )
            ):
                raise SiteConfigError(f"agents.{key}: {model_name} must be a regular API model")
            if model.get("read_only") and set(operations) - {"list", "get"}:
                raise SiteConfigError(f"agents.{key}: {model_name} is read-only")
            if "import" in operations and not model.get("importable"):
                raise SiteConfigError(f"agents.{key}: {model_name} must enable importable for import")
            for operation in operations:
                name = f"{model_name}_{operation}"
                if name in names or len(name) > 64:
                    raise SiteConfigError(f"Duplicate or too long agent tool name: {name}")
                names.add(name)
            metadata[model_name] = {
                "path": f"/{model['module_name']}s",
                "roles": model["role_permissions"],
                "fields": {
                    f["name"]: (
                        {role: "r" for role in ("user", "admin", "developer")}
                        if f["name"] == "id"
                        else (
                            f.get("role_permissions")
                            or {
                                role: f.get("permissions", "")
                                for role in ("user", "admin", "developer")
                            }
                        )
                    )
                    for f in model["fields"]
                },
            }
            # Composite-key APIs expose an encoded id even without a physical id column.
            metadata[model_name]["fields"].setdefault(
                "id", {role: "r" for role in ("user", "admin", "developer")}
            )
    target = backend / "app/agent_tools"
    target.mkdir(parents=True, exist_ok=True)
    (target / "__init__.py").write_text("", encoding="utf-8")
    custom = sorted({name for agent in agents.values() for name in agent["custom_tools"]})
    source = paths.source / "agent_tools"
    if custom:
        source.mkdir(parents=True, exist_ok=True)
    for name in custom:
        path = source / f"{name}.py"
        if not path.exists():
            path.write_text(
                "from pydantic import BaseModel\nfrom app.core.agent_tools import agent_tool\n\n\n"
                "class Arguments(BaseModel):\n    pass\n\n\n"
                f"@agent_tool(args_model=Arguments)\nasync def {name}(args, context):\n"
                f'    """{name}: replace this description and implement this tool."""\n'
                '    raise NotImplementedError("Implement this tool in app/agent_tools")\n',
                encoding="utf-8",
            )
        _validate_function(path, name)
    if source.exists():
        for path in source.rglob("*.py"):
            copy_file_with_status(path, target / path.relative_to(source))
        for path in target.rglob("*.py"):
            if path.name != "__init__.py" and not (source / path.relative_to(target)).exists():
                path.unlink()
    hook_names = sorted(
        {handler.split(".")[1] for a in agents.values() for handler in a["hooks"].values()}
    )
    hooks_path = paths.source / "agent_hooks.py"
    if hook_names and not hooks_path.exists():
        hooks_path.parent.mkdir(parents=True, exist_ok=True)
        hooks_path.write_text(
            "\n\n".join(
                f"async def {name}(event, context):\n    return None\n" for name in hook_names
            ),
            encoding="utf-8",
        )
    for name in hook_names:
        _validate_function(hooks_path, name)
    if hooks_path.exists():
        copy_file_with_status(hooks_path, backend / "app/agent_hooks.py")
    context = {
        "agents_json": json.dumps(agents, ensure_ascii=False),
        "models_json": json.dumps(metadata, ensure_ascii=False),
    }
    for template, path in outputs.items():
        generate_file(template, context, path)
    requirements = backend / "requirements.txt"
    existing = requirements.read_text() if requirements.exists() else ""
    for dependency in ("openai>=1.0", "jsonschema>=4.0"):
        if dependency not in existing.splitlines():
            existing += f"\n{dependency}\n"
    requirements.write_text(existing, encoding="utf-8")
