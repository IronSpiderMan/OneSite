"""Build project-specific Python SDK wheels from the project's OpenAPI document."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import json
import keyword
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any

from packaging.version import Version

from .project_paths import get_project_paths

CRUD_METHODS = {"list": "get", "get": "get", "create": "post", "update": "put", "delete": "delete"}
EXPORT_SCHEMA = """\
import json
from pathlib import Path
import sys

from app.main import app

Path(sys.argv[1]).write_text(json.dumps(app.openapi()), encoding="utf-8")
"""


class SDKBuildError(Exception):
    """The SDK could not be generated from the supplied project or schema."""


@dataclass(frozen=True)
class Operation:
    method: str
    path: str
    namespace: str
    name: str
    parameters: list[dict[str, Any]]
    definition: dict[str, Any]


def _identifier(text: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower() or "api"
    if name[0].isdigit():
        name = "api_" + name
    return name + "_" if keyword.iskeyword(name) else name


def _class_name(name: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in name.split("_") if part)


def _unique(name: str, used: set[str]) -> str:
    candidate = name
    suffix = 2
    while candidate in used:
        candidate = f"{name}_{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def _resolve(spec: dict[str, Any], value: dict[str, Any]) -> dict[str, Any]:
    seen = set()
    while ref := value.get("$ref"):
        if not ref.startswith("#/") or ref in seen:
            raise SDKBuildError(f"Cannot resolve OpenAPI reference {ref!r}")
        seen.add(ref)
        target = spec
        for part in ref[2:].split("/"):
            target = target[part.replace("~1", "/").replace("~0", "~")]
        value = target
    return value


def _model_names(schemas: dict[str, Any]) -> dict[str, str]:
    used = {
        "Any", "Literal", "NotRequired", "Required", "TypeAliasType", "TypedDict",
        "bool", "dict", "float", "int", "list", "str",
    }
    return {
        key: _unique(
            key if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key) and not keyword.iskeyword(key)
            else "Model" + _class_name(_identifier(key)),
            used,
        )
        for key in sorted(schemas)
    }


def _union(types: list[str]) -> str:
    return " | ".join(dict.fromkeys(types)) or "Any"


def _hint(schema: dict[str, Any], names: dict[str, str], prefix: str = "") -> str:
    if ref := schema.get("$ref"):
        name = names.get(ref.removeprefix("#/components/schemas/"))
        return prefix + name if name else "Any"
    if choices := schema.get("anyOf") or schema.get("oneOf"):
        return _union([_hint(choice, names, prefix) for choice in choices])
    if values := schema.get("enum"):
        if all(value is None or type(value) in {str, int, bool} for value in values):
            return f"Literal[{', '.join(repr(value) for value in values)}]"
    kind = schema.get("type")
    if isinstance(kind, list):
        return _union([_hint({**schema, "type": item}, names, prefix) for item in kind])
    if kind == "array":
        return f"list[{_hint(schema.get('items', {}), names, prefix)}]"
    if kind == "object" or "properties" in schema:
        values = schema.get("additionalProperties")
        return f"dict[str, {_hint(values, names, prefix)}]" if isinstance(values, dict) else "dict[str, Any]"
    hint = {"string": "str", "boolean": "bool", "integer": "int",
            "number": "float", "null": "None"}.get(kind, "Any")
    return f"{hint} | None" if schema.get("nullable") and hint not in {"Any", "None"} else hint


def _render_models(schemas: dict[str, Any], names: dict[str, str]) -> str:
    lines = [
        '"""Request and response types from the OpenAPI schema."""', "",
        "from typing import Any, Literal",
        "from typing_extensions import NotRequired, Required, TypeAliasType, TypedDict", "",
    ]
    for key, name in names.items():
        schema = schemas[key]
        required = set(schema.get("required", []))
        if fields := schema.get("properties"):
            lines.append(f'{name} = TypedDict({name!r}, {{')
            for field, definition in fields.items():
                qualifier = "Required" if field in required else "NotRequired"
                lines.append(f"    {field!r}: {qualifier}[{_hint(definition, names)!r}],")
            lines.extend(["}, total=False)", ""])
        else:
            lines.extend([f"{name} = TypeAliasType({name!r}, {_hint(schema, names)!r})", ""])
    return "\n".join(lines)


def _is_api_path(path: str) -> bool:
    return path.startswith("/") and not path.startswith("//") and not any(
        character in path for character in "?#\\"
    )


def _token_path(spec: dict[str, Any]) -> str:
    schemes = spec.get("components", {}).get("securitySchemes", {}).values()
    for scheme in schemes:
        token_url = _resolve(spec, scheme).get("flows", {}).get("password", {}).get("tokenUrl")
        if token_url:
            path = "/" + token_url.lstrip("/")
            if _is_api_path(path) and "post" in _resolve(spec, spec["paths"].get(path, {})):
                return path
            candidates = [
                candidate for candidate, item in spec["paths"].items()
                if _is_api_path(candidate) and candidate.endswith(path) and "post" in _resolve(spec, item)
            ]
            if len(candidates) == 1:
                return candidates[0]
    raise SDKBuildError("The schema must declare the OneSite OAuth2 password login endpoint")


def _operations(spec: dict[str, Any]) -> list[Operation]:
    operations = []
    groups: dict[str, str] = {}
    used_groups = {"login", "logout", "close"}
    used_names: dict[str, set[str]] = defaultdict(set)
    for path, item in sorted(spec["paths"].items()):
        item = _resolve(spec, item)
        for method in sorted(set(CRUD_METHODS.values()) & item.keys()):
            definition = item[method]
            name = definition.get("x-onesite-crud")
            if name is None:
                continue
            if CRUD_METHODS.get(name) != method:
                raise SDKBuildError(f"Invalid CRUD operation {name!r} for {method.upper()} {path}")
            if not _is_api_path(path):
                raise SDKBuildError(f"Invalid API path {path!r}")
            tags = definition.get("tags")
            if not tags:
                raise SDKBuildError(f"CRUD operation {method.upper()} {path} is missing its model tag")
            tag = tags[0]
            if tag not in groups:
                groups[tag] = _unique(_identifier(tag), used_groups)
            namespace = groups[tag]
            if name in used_names[namespace]:
                raise SDKBuildError(f"Multiple {name!r} operations for model tag {tag!r}")
            used_names[namespace].add(name)
            parameters = {}
            for source in (item, definition):
                for value in source.get("parameters", []):
                    parameter = _resolve(spec, value)
                    parameters[parameter["in"], parameter["name"]] = parameter
            operations.append(Operation(
                method, path, namespace, name, list(parameters.values()), definition
            ))
    return operations


def _model_schemas(spec: dict[str, Any], operations: list[Operation]) -> dict[str, Any]:
    """Collect schemas referenced by the selected CRUD operations, including nested models."""
    schemas: dict[str, Any] = {}
    prefix = "#/components/schemas/"
    visited: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str) and ref not in visited:
                visited.add(ref)
                target = _resolve(spec, {"$ref": ref})
                if ref.startswith(prefix):
                    schemas[ref.removeprefix(prefix)] = target
                visit(target)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for operation in operations:
        visit(operation.definition.get("requestBody", {}))
        visit(operation.definition.get("responses", {}))
        visit(operation.parameters)
    return schemas


def _success_type(spec: dict[str, Any], operation: Operation, names: dict[str, str]) -> str:
    types = []
    for status, entry in operation.definition.get("responses", {}).items():
        if not status.startswith("2"):
            continue
        content = _resolve(spec, entry).get("content", {})
        media = content.get("application/json")
        types.append(_hint(media.get("schema", {}), names, "_models.") if media else "None")
    return _union(types)


def _render_method(
    spec: dict[str, Any], operation: Operation, names: dict[str, str]
) -> list[str]:
    annotations: list[str] = []
    arguments: dict[str, dict[str, str]] = defaultdict(dict)
    options: dict[str, str] = {}
    used = {"self"}

    def parameter(wire_name: str, hint: str, required: bool, location: str) -> None:
        name = _unique(_identifier(wire_name), used)
        annotations.append(f"{name}: {hint}" if required else f"{name}: {hint} | None = None")
        arguments[location][wire_name] = name

    for field in operation.parameters:
        location = {"path": "path_params", "query": "query"}
        if field["in"] not in location:
            raise SDKBuildError(f"Unsupported parameter location {field['in']!r} in {operation.path}")
        parameter(field["name"], _hint(field.get("schema", {}), names, "_models."),
                  field.get("required", False), location[field["in"]])

    request = _resolve(spec, operation.definition.get("requestBody", {}))
    if request:
        media = request.get("content", {}).get("application/json")
        if media is None:
            raise SDKBuildError(f"Expected a JSON request body for {operation.method} {operation.path}")
        name = _unique("body", used)
        hint = _hint(media.get("schema", {}), names, "_models.")
        if not request.get("required", False):
            hint += " | Unset = _UNSET"
        annotations.append(f"{name}: {hint}")
        options["body"] = name
    for location, fields in arguments.items():
        options[location] = "{" + ", ".join(f"{key!r}: {value}" for key, value in fields.items()) + "}"
    result = _success_type(spec, operation, names)
    signature = ", *, " + ", ".join(annotations) if annotations else ""
    doc = f"{operation.method.upper()} {operation.path}"
    if summary := operation.definition.get("summary"):
        doc = f"{summary}. {doc}"
    lines = [
        f"    def {operation.name}(self{signature}) -> {result}:",
        f"        {doc!r}",
        "        return self._client._request(",
        f"            {operation.method.upper()!r}, {operation.path!r},",
    ]
    lines.extend(f"            {name}={value}," for name, value in options.items())
    return lines + ["        )", ""]


def _render_api(
    spec: dict[str, Any], operations: list[Operation], names: dict[str, str], client_name: str
) -> str:
    token_path = _token_path(spec)
    groups: dict[str, list[Operation]] = defaultdict(list)
    for operation in operations:
        groups[operation.namespace].append(operation)
    lines = [
        '"""Client methods generated from the OpenAPI schema."""',
        "from __future__ import annotations", "",
        "from typing import Any, Literal",
        "import httpx",
        "from . import models as _models",
        "from ._transport import HTTPClient, Unset, _UNSET", "",
        "# An index of every operation in this SDK, keyed by HTTP method and path.",
        "OPERATIONS = {",
    ]
    lines.extend(
        f"    ({op.method.upper()!r}, {op.path!r}): ({op.namespace!r}, {op.name!r}),"
        for op in operations
    )
    lines.extend(["}", ""])
    group_types = {
        name: f"_{name}_API" for name in groups
    }
    for name, group in groups.items():
        lines.extend([
            "", f"class {group_types[name]}:",
            "    def __init__(self, client: HTTPClient) -> None:",
            "        self._client = client", "",
        ])
        for operation in group:
            lines.extend(_render_method(spec, operation, names))
    lines.extend([
        "", f"class {client_name}(HTTPClient):",
        '    """Client for the project HTTP API."""',
        f"    _token_path = {token_path!r}", "",
        "    def __init__(self, base_url: str, *, token: str | None = None,",
        "                 timeout: float | httpx.Timeout = 30.0,",
        "                 transport: httpx.BaseTransport | None = None) -> None:",
        "        super().__init__(base_url, token=token, timeout=timeout, transport=transport)",
    ])
    lines.extend(f"        self.{name} = {group_types[name]}(self)" for name in groups)
    return "\n".join(lines) + "\n"


def _run(command: list[str], cwd: Path, action: str) -> str:
    completed = subprocess.run(
        [sys.executable, "-B", *command], cwd=cwd, text=True, capture_output=True,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise SDKBuildError(f"{action} failed.\n{detail}")
    return completed.stdout


def build_sdk(
    root: Path, output: Path | None = None, *, openapi: Path | None = None,
    name: str | None = None, version: str | None = None,
) -> Path:
    """Build a standalone wheel from a generated backend or an exported document."""
    config_path = root / "sdk.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {}
    if not isinstance(config, dict) or any(
        key not in {"name", "version", "output"} or not isinstance(value, str) or not value
        for key, value in config.items()
    ):
        raise SDKBuildError("sdk.json must contain only non-empty strings for name, version, or output")
    output = output if output is not None else root / config.get("output", "dist")
    name = name if name is not None else config.get("name")
    version = version if version is not None else config.get("version")
    with TemporaryDirectory(prefix="onesite-sdk-") as directory:
        stage = Path(directory)
        if openapi is None:
            backend = get_project_paths(root).backend
            if not (backend / "app" / "main.py").is_file():
                raise SDKBuildError("Generated backend is missing. Run site sync or pass --openapi.")
            openapi = stage / "openapi.json"
            _run(["-c", EXPORT_SCHEMA, str(openapi)], backend, "Loading the generated backend")
        spec = json.loads(openapi.read_text(encoding="utf-8"))
        if not isinstance(spec, dict) or not isinstance(spec.get("paths"), dict):
            raise SDKBuildError("Expected an OpenAPI JSON document with a paths object")
        operations = _operations(spec)
        if not operations:
            raise SDKBuildError("No custom model CRUD routes found. Run site sync with this version of OneSite.")
        info = spec.get("info", {})
        name = name or f"{_identifier(info.get('title', 'project')).replace('_', '-')}-sdk"
        if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?", name):
            raise SDKBuildError(f"Invalid distribution name {name!r}")
        package = _identifier(re.sub(r"[-_.]+", "_", name))
        version = str(Version(version or info.get("version") or "0.1.0"))
        client_name = _class_name(package.removesuffix("_sdk")) + "Client"
        schemas = _model_schemas(spec, operations)
        names = _model_names(schemas)
        sources = stage / "src" / package
        sources.mkdir(parents=True)
        (sources / "py.typed").touch()
        shutil.copyfile(Path(__file__).with_name("sdk_client.py"), sources / "_transport.py")
        (sources / "models.py").write_text(_render_models(schemas, names), encoding="utf-8")
        (sources / "_api.py").write_text(
            _render_api(spec, operations, names, client_name), encoding="utf-8"
        )
        exports = ["APIError", "AuthenticationExpired", "Client", client_name, "OPERATIONS", "models"]
        (sources / "__init__.py").write_text(
            "from . import models\n"
            f"from ._api import {client_name}, OPERATIONS\n"
            "from ._transport import APIError, AuthenticationExpired\n\n"
            f"Client = {client_name}\n"
            f"__all__ = {exports!r}\n",
            encoding="utf-8",
        )
        (stage / "pyproject.toml").write_text(
            '[build-system]\nrequires = ["setuptools>=70.1"]\n'
            'build-backend = "setuptools.build_meta"\n\n'
            f'[project]\nname = {json.dumps(name)}\nversion = {json.dumps(version)}\n'
            'requires-python = ">=3.10"\ndependencies = ["httpx>=0.27,<1", "typing-extensions>=4.6"]\n',
            encoding="utf-8",
        )
        wheels = stage / "wheels"
        wheels.mkdir()
        _run(["-c", "from setuptools.build_meta import build_wheel; build_wheel('wheels')"],
             stage, "Building the wheel")
        built_wheels = list(wheels.glob("*.whl"))
        if len(built_wheels) != 1:
            raise SDKBuildError("The build backend did not produce exactly one wheel")
        wheel = built_wheels[0]
        output.mkdir(parents=True, exist_ok=True)
        # Stage in the destination filesystem so concurrent consumers see whole wheels.
        with TemporaryDirectory(prefix=".sdk-", dir=output) as destination:
            completed = Path(destination) / wheel.name
            shutil.copyfile(wheel, completed)
            return completed.replace(output / wheel.name)
