"""Model capability contracts and generated artifacts."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import inspect
from sqlalchemy.orm import ColumnProperty

from ..config import CapabilityKind, ModelCapabilityConfig, UniversalCapabilityConfig
from .metadata.fields import _unwrap_optional
from .render import generate_file


@dataclass(frozen=True)
class Capability:
    fields: dict[str, type]
    operations: tuple[str, ...]
    component: str
    optional_fields: dict[str, type] = field(default_factory=dict)
    nullable_fields: frozenset[str] = frozenset()
    dependencies: tuple[str, ...] = ()
    adapter: str = ""
    credential: str | None = None


CAPABILITIES = {
    CapabilityKind.OPCUA_SERVER: Capability(
        {"endpoint": str, "username": str, "password": str}, ("browse",),
        "OpcuaCapability",
        optional_fields={
            "auth_type": str, "security_policy": str, "security_mode": str,
            "app_uri": str, "cert_path": str, "key_path": str,
            "server_cert_path": str, "request_timeout_seconds": float,
        },
        nullable_fields=frozenset({"username", "password"}),
        dependencies=("asyncua>=1.1.5,<2",), adapter="opcua", credential="password",
    ),
    CapabilityKind.MQTT_BROKER: Capability(
        {"endpoint": str, "username": str, "password": str}, ("subscribe",),
        "MqttCapability", nullable_fields=frozenset({"username", "password"}),
        dependencies=("gmqtt",), adapter="mqtt", credential="password",
    ),
    CapabilityKind.DATABASE: Capability(
        {"host": str, "port": int, "username": str, "password": str,
         "database": str, "driver": Enum}, ("list_tables", "read_rows", "query"),
        "DatabaseCapability", adapter="database", credential="password",
    ),
}

PROFILE_ROLES = ("admin", "developer")
DATABASE_DRIVERS = {"postgresql"}


_CAPABILITY_CONFIG = TypeAdapter(ModelCapabilityConfig)


def _model_column(model, mapper, name, path):
    model_field = model.model_fields.get(name)
    prop = mapper.get_property(name) if mapper.has_property(name) else None
    if model_field is None or not isinstance(prop, ColumnProperty):
        raise ValueError(f"{path}: model field {name!r} does not exist as a column")
    column = prop.columns[0]
    if column.primary_key or name in {"id", "created_at", "updated_at"}:
        raise ValueError(f"{path}: {name!r} is reserved")
    if column.foreign_keys:
        raise ValueError(f"{path}: {name!r} cannot be a foreign key")
    return model_field, column


def _is_string_enum(annotation):
    return isinstance(annotation, type) and issubclass(annotation, str) and issubclass(annotation, Enum)


def _compile_adapter(model, mapper, config, path, *, conditional=False):
    spec = CAPABILITIES[config.kind]
    unknown_fields = config.field_map.keys() - (spec.fields.keys() | spec.optional_fields.keys())
    if unknown_fields:
        raise ValueError(f"{path}.field_map has unknown fields: {', '.join(sorted(unknown_fields))}")
    unknown_operations = config.permissions.keys() - set(spec.operations)
    if unknown_operations:
        raise ValueError(f"{path}.permissions has unknown operations: {', '.join(sorted(unknown_operations))}")

    mapping = {}
    for semantic, expected in (spec.fields | spec.optional_fields).items():
        name = config.field_map.get(semantic, semantic)
        if semantic in spec.optional_fields and semantic not in config.field_map and name not in model.model_fields:
            continue
        location = f"{path}.{semantic}"
        model_field, column = _model_column(model, mapper, name, location)
        annotation, optional = _unwrap_optional(model_field.annotation)
        if expected is Enum:
            if not _is_string_enum(annotation):
                raise ValueError(f"{location}: {name!r} must be a string enum")
            values = {item.value for item in annotation}
            if not values or values - DATABASE_DRIVERS:
                raise ValueError(f"{location}: supported values are {', '.join(sorted(DATABASE_DRIVERS))}")
        elif annotation is not expected and not (
            semantic in spec.optional_fields and isinstance(annotation, type)
            and (expected is str and issubclass(annotation, str) or expected is float and annotation is int)
        ):
            raise ValueError(f"{location}: {name!r} must have type {expected.__name__}")
        if not conditional and semantic in spec.fields and semantic not in spec.nullable_fields and optional:
            raise ValueError(f"{location}: {name!r} must be non-nullable")
        if semantic == spec.credential:
            if ((not model_field.is_required() and model_field.default not in (None, ""))
                    or model_field.default_factory or column.server_default is not None):
                raise ValueError(f"{location}: use a blank default or supply the value when creating the record")
            if column.unique:
                raise ValueError(f"{location}: a capability password cannot be unique")
        if name in mapping.values():
            raise ValueError(f"{path}.field_map maps multiple fields to {name!r}")
        mapping[semantic] = name

    return {
        "kind": config.kind.value,
        "fields": mapping,
        "permissions": {op: list(config.permissions.get(op, PROFILE_ROLES)) for op in spec.operations},
        "component": spec.component,
        "adapter": spec.adapter,
        "credential": spec.credential,
    }


def _compile_universal(model, mapper, config, path):
    selector = config.selector_field
    model_field, column = _model_column(model, mapper, selector, f"{path}.selector_field")
    annotation, optional = _unwrap_optional(model_field.annotation)
    if not _is_string_enum(annotation) or optional or column.nullable:
        raise ValueError(f"{path}.selector_field: {selector!r} must be a non-nullable string enum")
    values = {item.value for item in annotation}
    if not values or "" in values:
        raise ValueError(f"{path}.selector_field: {selector!r} must have non-empty enum values")
    covered = set()
    branches = []
    for key, branch in config.branches.items():
        branch_path = f"{path}.branches.{key}"
        when = branch.when if branch.when is not None else {selector: key}
        if when.keys() != {selector}:
            raise ValueError(f"{branch_path}.when must reference only {selector!r}")
        match = when[selector]
        matches = {match} if isinstance(match, str) else set(match)
        if not matches or matches - values:
            raise ValueError(f"{branch_path}.when must match one or more values of {selector!r}: {', '.join(sorted(values))}")
        if covered & matches:
            raise ValueError(f"{branch_path}.when overlaps for enum values: {', '.join(sorted(covered & matches))}")
        covered.update(matches)
        entry = _compile_adapter(model, mapper, branch, branch_path, conditional=True)
        spec = CAPABILITIES[branch.kind]
        entry.update(
            selector_field=selector,
            selector_values=sorted(matches),
            required_fields=[entry["fields"][name] for name in spec.fields if name not in spec.nullable_fields],
        )
        branches.append(entry)

    if values - covered:
        raise ValueError(f"{path} is missing branches for enum values: {', '.join(sorted(values - covered))}")
    return branches


def compile_capabilities(model, raw):
    """Validate declarations and compile Universal branches as concrete capabilities."""
    path = f"{model.__name__}.capabilities"
    if not isinstance(raw, (list, tuple)):
        raise ValueError(f"{path} must be a list")
    if not raw:
        return []

    mapper = inspect(model, raiseerr=False)
    if mapper is None:
        raise ValueError(f"{path} requires a table model")

    compiled = []
    seen = set()
    for entry in raw:
        try:
            config = _CAPABILITY_CONFIG.validate_python(entry)
        except ValidationError as exc:
            raise ValueError(f"{path}: {exc}") from None
        config_path = f"{path}.{config.kind.value}"
        if isinstance(config, UniversalCapabilityConfig):
            if config.kind.value in seen:
                raise ValueError(f"{config_path} is declared more than once")
            seen.add(config.kind.value)
            entries = _compile_universal(model, mapper, config, config_path)
        else:
            entries = [_compile_adapter(model, mapper, config, config_path)]
        for adapter in entries:
            kind = adapter["kind"]
            if kind in seen:
                raise ValueError(f"{path}.{kind} is declared more than once")
            seen.add(kind)
            compiled.append(adapter)

    secrets = {entry["fields"][entry["credential"]] for entry in compiled if entry["credential"]}
    if any(name in secrets for entry in compiled for semantic, name in entry["fields"].items() if semantic != entry["credential"]):
        raise ValueError(f"{path} cannot reuse a password field for another purpose")

    branches = [entry for entry in compiled if "selector_field" in entry]
    if branches:
        _validate_universal_columns(model, mapper, compiled, branches, f"{path}.universal")
    return compiled


def _validate_universal_columns(model, mapper, compiled, branches, path):
    selector = branches[0]["selector_field"]
    if any(selector in entry["fields"].values() for entry in compiled):
        raise ValueError(f"{path}.selector_field: {selector!r} cannot also be a mapped connection field")

    branch_fields = [set(entry["fields"].values()) for entry in branches]
    always_active = set.intersection(*branch_fields)
    always_active.update(
        name for entry in compiled if "selector_field" not in entry for name in entry["fields"].values()
    )
    for name in sorted(set.union(*branch_fields) - always_active):
        model_field, column = _model_column(model, mapper, name, path)
        _, optional = _unwrap_optional(model_field.annotation)
        if model_field.is_required() or (model_field.default is None and not (optional and column.nullable)):
            raise ValueError(f"{path}: branch-specific field {name!r} needs a default or a nullable type with default None")


def generate_capabilities(models, backend_path: Path, frontend_path: Path):
    enabled = [model for model in models if model.get("capabilities")]
    if not enabled:
        return False
    kinds = {entry["kind"] for model in enabled for entry in model["capabilities"]}
    for kind, spec in CAPABILITIES.items():
        if kind.value not in kinds or kind is CapabilityKind.OPCUA_SERVER:
            continue
        generate_file(
            f"capability_{spec.adapter}_api.py.j2", {},
            backend_path / f"app/api/endpoints/capability_{spec.adapter}.py",
        )
        generate_file(
            f"capability_{spec.adapter}.tsx.j2", {},
            frontend_path / f"src/components/capabilities/{spec.component}.tsx",
        )
    generate_file("model_capability_profiles.py.j2", {}, backend_path / "app/core/capability_profiles.py")
    generate_file(
        "model_capabilities_api.py.j2",
        {"models": enabled, "adapters": sorted({CAPABILITIES[kind].adapter for kind in kinds})},
        backend_path / "app/api/endpoints/model_capabilities.py",
    )
    if CapabilityKind.MQTT_BROKER.value in kinds:
        generate_file(
            "model_capability_mqtt_page.tsx.j2", {},
            frontend_path / "src/components/capabilities/MqttCapabilityPage.tsx",
        )
    return True
