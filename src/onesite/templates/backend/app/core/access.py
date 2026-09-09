"""Request-scoped authorization shared by generated schemas and queries."""

from contextvars import ContextVar
from importlib import import_module
from typing import Any, ClassVar

from fastapi import HTTPException
from pydantic import model_serializer, model_validator
from sqlmodel import SQLModel

current_actor: ContextVar[Any] = ContextVar("onesite_actor", default=None)


def role_of(user: Any) -> str:
    role = getattr(user, "role", "")
    return str(getattr(role, "value", role))


def require_operation(permissions: dict, operation: str, user: Any) -> None:
    if any(char not in permissions.get(role_of(user), "") for char in operation):
        raise HTTPException(status_code=403, detail="Permission denied")


class ReadModel(SQLModel):
    __read_permissions__: ClassVar[dict[str, dict[str, str]]] = {}

    @model_serializer(mode="wrap")
    def serialize_for_actor(self, serializer):
        data = serializer(self)
        user = current_actor.get()
        if user is None:
            return data  # Internal code has no request principal.
        role = role_of(user)
        for name, permissions in self.__read_permissions__.items():
            if "r" not in permissions.get(role, ""):
                data.pop(name, None)
                data.pop(name + "_label", None)
                data.pop(name + "__raw", None)
        return data


class WriteModel(SQLModel):
    __write_permissions__: ClassVar[dict[str, dict[str, str]]] = {}
    __write_operation__: ClassVar[str] = "u"
    __owner_field__: ClassVar[str] = ""

    @model_validator(mode="before")
    @classmethod
    def validate_writable_fields(cls, value):
        user = current_actor.get()
        if user is not None and isinstance(value, dict):
            role = role_of(user)
            owner = cls.__owner_field__
            if owner and role not in {"admin", "developer"} and owner in value and str(value[owner]) != str(user.id):
                raise HTTPException(status_code=403, detail="Cannot assign another owner")
            forbidden = [
                name for name in value
                if name in cls.__write_permissions__
                and cls.__write_operation__ not in cls.__write_permissions__[name].get(role, "")
            ]
            if forbidden:
                raise HTTPException(status_code=403, detail={
                    "message": "Fields are not writable", "fields": sorted(forbidden),
                })
            if owner and cls.__write_operation__ == "c" and role not in {"admin", "developer"} and owner not in value:
                value = {**value, owner: user.id}
        return value


def policy_for(key: str) -> dict:
    from app.core.access_policies import POLICIES
    return POLICIES[key]


def policy_key_for_model(model: Any, key: str) -> str:
    """Resolve a missing generated policy key from the SQLModel table name.

    FK label lookups must be permission-scoped too.  Older generated CRUD
    modules can carry an empty relationship service name, while the target
    model remains available.  The table name is the OneSite policy key by
    convention, so it provides a safe compatibility fallback.
    """
    if key:
        return key
    table_name = getattr(model, "__tablename__", None)
    return str(table_name) if table_name else ""


def scope_statement(statement, model, key: str):
    """Apply target read permission and owner scope before pagination/counting."""
    user = current_actor.get()
    if user is None:
        return statement
    policy = policy_for(key)
    require_operation(policy["permissions"], "r", user)
    owner = policy.get("owner_field")
    if owner and role_of(user) not in {"admin", "developer"}:
        statement = statement.where(getattr(model, owner) == user.id)
    return statement


async def require_owned_record(session, key: str, identity: Any, user: Any = None):
    user = user or current_actor.get()
    if user is None:
        return
    policy = policy_for(key)
    crud = import_module(f"app.cruds.{key}")
    record = await crud.get(session, identity)
    owner = policy.get("owner_field")
    if record is None or (
        owner and role_of(user) not in {"admin", "developer"}
        and getattr(record, owner, None) != user.id
    ):
        raise HTTPException(status_code=404, detail="Record not found")


async def require_relation(session, source: str, target: str, identity: Any):
    user = current_actor.get()
    if user is None:
        return
    require_operation(policy_for(source)["permissions"], "r", user)
    require_operation(policy_for(target)["permissions"], "r", user)
    await require_owned_record(session, source, identity, user)


def scope_label_statement(statement, model, key: str):
    from sqlalchemy import false
    key = policy_key_for_model(model, key)
    if not key:
        # Missing policy metadata must not turn a label enrichment query into
        # a 500 response or disclose rows outside the caller's scope.
        return statement.where(false())
    user = current_actor.get()
    if user is not None and "r" not in policy_for(key)["permissions"].get(role_of(user), ""):
        return statement.where(false())
    return scope_statement(statement, model, key)


def filter_read_data(data, key: str):
    user = current_actor.get()
    if user is None:
        return data
    if isinstance(data, list):
        return [filter_read_data(item, key) for item in data]
    if isinstance(data, dict):
        fields = policy_for(key)["fields"]
        return {name: value for name, value in data.items()
                if name not in fields or "r" in fields[name].get(role_of(user), "")}
    return data
