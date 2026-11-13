"""Model capability contracts and generated artifacts."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import inspect

from ..config import CapabilityConfig, CapabilityKind
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


def compile_capabilities(model, raw):
    """Validate declarations against actual mapped SQLModel field types."""
    if not isinstance(raw, (list, tuple)):
        raise ValueError(f"{model.__name__}.capabilities must be a list")

    compiled = []
    seen = set()
    for entry in raw:
        try:
            config = CapabilityConfig.model_validate(entry)
        except ValidationError as exc:
            raise ValueError(f"{model.__name__}.capabilities: {exc}") from None
        kind = config.kind
        path = f"{model.__name__}.capabilities.{kind.value}"
        if kind in seen:
            raise ValueError(f"{path} is declared more than once")
        seen.add(kind)
        spec = CAPABILITIES[kind]
        unknown_fields = config.field_map.keys() - (spec.fields.keys() | spec.optional_fields.keys())
        if unknown_fields:
            raise ValueError(f"{path}.field_map has unknown fields: {', '.join(sorted(unknown_fields))}")
        unknown_operations = config.permissions.keys() - set(spec.operations)
        if unknown_operations:
            raise ValueError(f"{path}.permissions has unknown operations: {', '.join(sorted(unknown_operations))}")

        mapper = inspect(model, raiseerr=False)
        if mapper is None:
            raise ValueError(f"{path} requires a table model")
        mapping = {}
        for semantic, expected in (spec.fields | spec.optional_fields).items():
            name = config.field_map.get(semantic, semantic)
            if semantic in spec.optional_fields and semantic not in config.field_map and name not in model.model_fields:
                continue
            model_field = model.model_fields.get(name)
            prop = mapper.column_attrs.get(name)
            if model_field is None or prop is None:
                raise ValueError(f"{path}.{semantic}: model field {name!r} does not exist as a column")
            column = prop.columns[0]
            if column.primary_key or name in {"id", "created_at", "updated_at"}:
                raise ValueError(f"{path}.{semantic}: {name!r} is reserved")
            if column.foreign_keys:
                raise ValueError(f"{path}.{semantic}: {name!r} cannot be a foreign key")
            annotation, optional = _unwrap_optional(model_field.annotation)
            if expected is Enum:
                if not isinstance(annotation, type) or not issubclass(annotation, str) or not issubclass(annotation, Enum):
                    raise ValueError(f"{path}.{semantic}: {name!r} must be a string enum")
                values = {item.value for item in annotation}
                if not values or values - DATABASE_DRIVERS:
                    raise ValueError(f"{path}.{semantic}: supported values are {', '.join(sorted(DATABASE_DRIVERS))}")
            elif annotation is not expected and not (
                semantic in spec.optional_fields and isinstance(annotation, type)
                and (expected is str and issubclass(annotation, str) or expected is float and annotation is int)
            ):
                raise ValueError(f"{path}.{semantic}: {name!r} must have type {expected.__name__}")
            if semantic in spec.fields and semantic not in spec.nullable_fields and optional:
                raise ValueError(f"{path}.{semantic}: {name!r} must be non-nullable")
            if semantic == spec.credential:
                if ((not model_field.is_required() and model_field.default not in (None, ""))
                        or model_field.default_factory or column.server_default is not None):
                    raise ValueError(f"{path}.{semantic}: use a blank default or supply the value when creating the record")
                if column.unique:
                    raise ValueError(f"{path}.{semantic}: a capability password cannot be unique")
            if name in mapping.values():
                raise ValueError(f"{path}.field_map maps multiple fields to {name!r}")
            mapping[semantic] = name

        compiled.append({
            "kind": kind.value,
            "fields": mapping,
            "permissions": {op: list(config.permissions.get(op, PROFILE_ROLES)) for op in spec.operations},
            "component": spec.component,
            "adapter": spec.adapter,
            "credential": spec.credential,
        })

    secrets = {entry["fields"][entry["credential"]] for entry in compiled if entry["credential"]}
    if any(name in secrets for entry in compiled for semantic, name in entry["fields"].items() if semantic != entry["credential"]):
        raise ValueError(f"{model.__name__}.capabilities cannot reuse a password field for another purpose")
    return compiled


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
