"""Small runtime API shared by OneSite model sources and generated backends.

This package intentionally has no FastAPI, SQLModel, or generator dependency.
``site sync`` copies it into the generated backend so model modules can use the
same action decorators while being introspected and while serving requests.
"""

from __future__ import annotations

import inspect
import asyncio
import ssl
from dataclasses import dataclass
from typing import Any, Callable, Literal, Mapping, TypeVar, overload
from urllib.parse import urlsplit


ACTION_METADATA_ATTRIBUTE = "__onesite_action__"
EXTRA_FIELD_METADATA_ATTRIBUTE = "__onesite_extra_field__"
OVERRIDE_FIELD_METADATA_ATTRIBUTE = "__onesite_override_field__"


@dataclass
class ActionContext:
    """Request-scoped values made available to action and availability methods."""

    session: Any
    user: Any
    action_name: str

    @property
    def current_user(self) -> Any:
        """Alias matching the name used by generated API dependencies."""

        return self.user


@dataclass
class ActionState:
    """Frontend presentation and executability of one action for one object."""

    visible: bool = True
    enabled: bool = True
    reason: str | None = None
    label: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "visible": self.visible,
            "enabled": self.enabled,
        }
        if self.reason is not None:
            result["reason"] = self.reason
        if self.label is not None:
            result["label"] = self.label
        return result


@dataclass
class ActionMetadata:
    """Metadata attached to a model method by :func:`action`."""

    permissions: str = "da"
    label: str | None = None
    unavailable: Literal["hide", "disable"] = "hide"
    condition: dict[str, Any] | None = None
    availability_handler: str | None = None


@dataclass(frozen=True)
class ReadContext:
    """Request-scoped values available while building a Read response.

    ``values`` is a snapshot of the database-backed response data before any
    override or extra-field resolver runs.  Resolvers must treat it as read
    only; their return values are merged into a separate response dictionary.
    """

    session: Any
    current_user: Any | None = None
    source: str = "detail"
    values: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class WriteContext:
    """Request-scoped values available while normalizing a field for storage."""

    session: Any
    current_user: Any | None = None
    operation: Literal["create", "update"] = "update"
    values: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ExtraFieldMetadata:
    """Metadata attached to an instance method by :func:`extra_field`."""

    name: str | None = None
    label: str | dict[str, str] | None = None
    show_in_list: bool = True
    show_in_detail: bool = True


@dataclass(frozen=True)
class NetworkDeviceMetadata:
    """Configuration for a response-only network reachability field."""

    url_field: str
    status_field: str = "online"
    checker: str | None = None
    timeout: float = 1.0
    udp_payload: str = ""


@dataclass(frozen=True)
class OverrideFieldMetadata:
    """Metadata attached to an instance method by :func:`override_field`."""

    field: str
    direction: Literal["read", "write"] = "read"


ActionFunction = TypeVar("ActionFunction", bound=Callable[..., Any])


@overload
def extra_field(function: ActionFunction, /) -> ActionFunction: ...


@overload
def extra_field(
    function: None = None,
    /,
    *,
    name: str | None = None,
    label: str | dict[str, str] | None = None,
    show_in_list: bool = True,
    show_in_detail: bool = True,
) -> Callable[[ActionFunction], ActionFunction]: ...


def extra_field(
    function: ActionFunction | None = None,
    /,
    *,
    name: str | None = None,
    label: str | dict[str, str] | None = None,
    show_in_list: bool = True,
    show_in_detail: bool = True,
) -> ActionFunction | Callable[[ActionFunction], ActionFunction]:
    """Declare a developer-computed, read-only response field.

    The method name becomes the field name unless ``name=`` is provided.  The
    generator requires a return annotation and emits that field only on the
    generated ``XxxRead`` schema.
    """

    if name is not None and (not isinstance(name, str) or not name):
        raise ValueError("extra_field name must be a non-empty string")
    if not isinstance(show_in_list, bool) or not isinstance(show_in_detail, bool):
        raise ValueError("extra_field show_in_list and show_in_detail must be booleans")

    def decorate(handler: ActionFunction) -> ActionFunction:
        setattr(
            handler,
            EXTRA_FIELD_METADATA_ATTRIBUTE,
            ExtraFieldMetadata(
                name=name,
                label=label,
                show_in_list=show_in_list,
                show_in_detail=show_in_detail,
            ),
        )
        return handler

    if function is not None:
        return decorate(function)
    return decorate


def override_field(
    field: str, *, direction: Literal["read", "write"] = "read"
) -> Callable[[ActionFunction], ActionFunction]:
    """Declare a field presentation override or its inverse write normalizer.

    The default ``direction="read"`` transforms a persisted value for the
    response.  Pair it with ``direction="write"`` on a second instance method
    to turn submitted display values back into the persisted representation.
    Write resolvers receive ``value``, ``context``, ``session``,
    ``current_user``, and ``values``; ``context.operation`` is ``"create"`` or
    ``"update"``.
    """

    if not isinstance(field, str) or not field:
        raise ValueError("override_field field must be a non-empty string")
    if direction not in {"read", "write"}:
        raise ValueError("override_field direction must be 'read' or 'write'")

    def decorate(handler: ActionFunction) -> ActionFunction:
        setattr(
            handler,
            OVERRIDE_FIELD_METADATA_ATTRIBUTE,
            OverrideFieldMetadata(field=field, direction=direction),
        )
        return handler

    return decorate


@overload
def action(function: ActionFunction, /) -> ActionFunction: ...


@overload
def action(
    function: None = None,
    /,
    *,
    permissions: str = "da",
    label: str | None = None,
    unavailable: Literal["hide", "disable"] = "hide",
    condition: dict[str, Any] | None = None,
) -> Callable[[ActionFunction], ActionFunction]: ...


def action(
    function: ActionFunction | None = None,
    /,
    *,
    permissions: str = "da",
    label: str | None = None,
    unavailable: Literal["hide", "disable"] = "hide",
    condition: dict[str, Any] | None = None,
) -> ActionFunction | Callable[[ActionFunction], ActionFunction]:
    """Mark an instance method as a generated model action.

    Both ``@action`` and ``@action(...)`` are supported.  A dynamic guard can
    be registered immediately below the action with ``@method.available``.
    The original function is returned unchanged so SQLModel sees an ordinary
    method rather than a custom descriptor.
    """

    if unavailable not in {"hide", "disable"}:
        raise ValueError("action unavailable must be either 'hide' or 'disable'")
    if not isinstance(permissions, str) or any(char not in "uad" for char in permissions):
        raise ValueError("action permissions may only contain 'u', 'a', and 'd'")

    def decorate(handler: ActionFunction) -> ActionFunction:
        metadata = ActionMetadata(
            permissions=permissions,
            label=label,
            unavailable=unavailable,
            condition=condition,
        )
        setattr(handler, ACTION_METADATA_ATTRIBUTE, metadata)

        def available(guard: ActionFunction) -> ActionFunction:
            if metadata.availability_handler is not None:
                raise ValueError(f"Action {handler.__name__!r} already has an availability method")
            metadata.availability_handler = guard.__name__
            return guard

        # Functions have a writable attribute namespace.  Keeping the original
        # handler makes the decorator transparent to SQLModel and SQLAlchemy.
        setattr(handler, "available", available)
        return handler

    if function is not None:
        return decorate(function)
    return decorate


def get_action_metadata(function: Any) -> ActionMetadata | None:
    """Return metadata from an unbound or bound decorated action method."""

    raw_function = getattr(function, "__func__", function)
    metadata = getattr(raw_function, ACTION_METADATA_ATTRIBUTE, None)
    return metadata if isinstance(metadata, ActionMetadata) else None


def get_extra_field_metadata(function: Any) -> ExtraFieldMetadata | None:
    """Return metadata from an unbound or bound extra-field resolver."""

    raw_function = getattr(function, "__func__", function)
    metadata = getattr(raw_function, EXTRA_FIELD_METADATA_ATTRIBUTE, None)
    return metadata if isinstance(metadata, ExtraFieldMetadata) else None


def get_override_field_metadata(function: Any) -> OverrideFieldMetadata | None:
    """Return metadata from an unbound or bound override-field resolver."""

    raw_function = getattr(function, "__func__", function)
    metadata = getattr(raw_function, OVERRIDE_FIELD_METADATA_ATTRIBUTE, None)
    return metadata if isinstance(metadata, OverrideFieldMetadata) else None


async def invoke_action_callable(function: Callable[..., Any], context: ActionContext) -> Any:
    """Invoke a validated action/guard with supported named dependencies."""

    signature = inspect.signature(function)
    parameters = signature.parameters
    has_kwargs = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )
    values = {
        "context": context,
        "session": context.session,
        "current_user": context.current_user,
    }
    kwargs = {
        name: value
        for name, value in values.items()
        if has_kwargs or name in parameters
    }
    result = function(**kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


async def invoke_read_callable(
    function: Callable[..., Any],
    context: ReadContext,
    *,
    value: Any = None,
    include_value: bool = False,
) -> Any:
    """Invoke a validated read resolver with its declared dependencies."""

    signature = inspect.signature(function)
    parameters = signature.parameters
    has_kwargs = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )
    values = {
        "context": context,
        "session": context.session,
        "current_user": context.current_user,
        "values": context.values,
    }
    if include_value:
        values["value"] = value
    kwargs = {
        name: resolved
        for name, resolved in values.items()
        if has_kwargs or name in parameters
    }
    result = function(**kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


async def invoke_write_callable(
    function: Callable[..., Any], context: WriteContext, *, value: Any
) -> Any:
    """Invoke a write-side override resolver with its declared dependencies."""

    signature = inspect.signature(function)
    parameters = signature.parameters
    has_kwargs = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )
    values = {
        "context": context,
        "session": context.session,
        "current_user": context.current_user,
        "values": context.values,
        "value": value,
    }
    kwargs = {
        name: resolved
        for name, resolved in values.items()
        if has_kwargs or name in parameters
    }
    result = function(**kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


_NETWORK_DEFAULT_PORTS = {
    "http": 80, "https": 443, "ws": 80, "wss": 443,
    "mqtt": 1883, "mqtts": 8883, "opc.tcp": 4840, "opcua": 4840,
    "modbus": 502, "modbus.tcp": 502, "rtsp": 554,
    "ftp": 21, "ssh": 22, "telnet": 23,
    "smtp": 25, "smtps": 465, "imap": 143, "imaps": 993,
    "pop3": 110, "pop3s": 995, "amqp": 5672, "amqps": 5671,
    "redis": 6379,
}
_TLS_SCHEMES = {"https", "wss", "mqtts", "smtps", "imaps", "pop3s", "amqps"}


async def _probe_tcp(host: str, port: int, timeout: float, *, use_tls: bool) -> bool:
    ssl_context = None
    if use_tls:
        # Reachability is independent from certificate trust.  Industrial and
        # embedded devices commonly use private or self-signed certificates.
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
    _, writer = await asyncio.wait_for(
        asyncio.open_connection(host, port, ssl=ssl_context), timeout=timeout
    )
    writer.close()
    try:
        await writer.wait_closed()
    except OSError:
        # A peer that resets while we close was still reachable.
        pass
    return True


class _UDPProbe(asyncio.DatagramProtocol):
    def __init__(self, future: asyncio.Future[bool]) -> None:
        self.future = future

    def datagram_received(self, data: bytes, addr: Any) -> None:
        if not self.future.done():
            self.future.set_result(True)

    def error_received(self, exc: Exception) -> None:
        if not self.future.done():
            self.future.set_result(False)


async def _probe_udp(host: str, port: int, timeout: float, payload: str) -> bool:
    loop = asyncio.get_running_loop()
    future: asyncio.Future[bool] = loop.create_future()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: _UDPProbe(future), remote_addr=(host, port)
    )
    try:
        transport.sendto(payload.encode())
        return await asyncio.wait_for(future, timeout=timeout)
    finally:
        transport.close()


async def probe_network_url(url: Any, *, timeout: float = 1.0, udp_payload: str = "") -> bool:
    """Return whether a URL endpoint is reachable without raising probe errors.

    HTTP-family endpoints are considered online when a TCP/TLS connection can
    be established.  This intentionally treats authentication and non-2xx
    responses as online: the feature measures reachability, not application
    health.  UDP requires a reply to the configured payload.
    """

    if not isinstance(url, str) or not url.strip():
        return False
    try:
        parsed = urlsplit(url.strip())
        scheme = parsed.scheme.lower()
        host = parsed.hostname
        if not scheme or not host:
            return False
        port = parsed.port or _NETWORK_DEFAULT_PORTS.get(scheme)
        if port is None:
            return False
        if scheme == "udp":
            return await _probe_udp(host, port, timeout, udp_payload)
        if scheme == "tcp" or scheme in _NETWORK_DEFAULT_PORTS:
            return await _probe_tcp(host, port, timeout, use_tls=scheme in _TLS_SCHEMES)
        return False
    except (OSError, ValueError, asyncio.TimeoutError, ssl.SSLError):
        return False


async def resolve_network_device_status(
    obj: Any,
    context: ReadContext,
    metadata: NetworkDeviceMetadata,
) -> bool:
    """Resolve configured reachability through a custom checker or URL scheme."""

    url = getattr(obj, metadata.url_field, None)
    if metadata.checker:
        try:
            checker = getattr(obj, metadata.checker)
            checker_context = ReadContext(
                session=context.session,
                current_user=context.current_user,
                source=context.source,
                values=context.values,
            )
            signature = inspect.signature(checker)
            parameters = signature.parameters
            has_kwargs = any(
                parameter.kind is inspect.Parameter.VAR_KEYWORD
                for parameter in parameters.values()
            )
            available = {
                "url": url,
                "context": checker_context,
                "session": checker_context.session,
                "current_user": checker_context.current_user,
                "values": checker_context.values,
            }
            kwargs = {
                name: value for name, value in available.items()
                if has_kwargs or name in parameters
            }
            result = checker(**kwargs)
            if inspect.isawaitable(result):
                result = await result
            return result if isinstance(result, bool) else False
        except Exception:
            return False
    return await probe_network_url(
        url, timeout=metadata.timeout, udp_payload=metadata.udp_payload
    )


async def resolve_read_data(
    obj: Any,
    data: Mapping[str, Any],
    context: ReadContext,
    network_device: NetworkDeviceMetadata | None = None,
) -> dict[str, Any]:
    """Apply all decorators declared on ``obj`` without mutating the ORM row."""

    result = dict(data)
    snapshot = dict(data)
    resolver_context = ReadContext(
        session=context.session,
        current_user=context.current_user,
        source=context.source,
        values=snapshot,
    )
    methods = vars(type(obj)).items()
    for _, raw_method in methods:
        metadata = get_override_field_metadata(raw_method)
        if metadata is None or metadata.direction != "read":
            continue
        resolver = getattr(obj, raw_method.__name__)
        result[metadata.field] = await invoke_read_callable(
            resolver,
            resolver_context,
            value=result.get(metadata.field),
            include_value=True,
        )
    for method_name, raw_method in methods:
        metadata = get_extra_field_metadata(raw_method)
        if metadata is None:
            continue
        resolver = getattr(obj, method_name)
        result[metadata.name or method_name] = await invoke_read_callable(
            resolver, resolver_context
        )
    if network_device is not None:
        result[network_device.status_field] = await resolve_network_device_status(
            obj, resolver_context, network_device
        )
    return result


async def resolve_write_data(
    obj: Any, data: Mapping[str, Any], context: WriteContext
) -> dict[str, Any]:
    """Normalize submitted values through declared write-side overrides."""

    result = dict(data)
    snapshot = dict(data)
    resolver_context = WriteContext(
        session=context.session,
        current_user=context.current_user,
        operation=context.operation,
        values=snapshot,
    )
    for _, raw_method in vars(type(obj)).items():
        metadata = get_override_field_metadata(raw_method)
        if metadata is None or metadata.direction != "write":
            continue
        if metadata.field not in result:
            continue
        resolver = getattr(obj, raw_method.__name__)
        result[metadata.field] = await invoke_write_callable(
            resolver, resolver_context, value=result[metadata.field]
        )
    return result


def normalize_action_state(
    value: bool | ActionState | None,
    *,
    unavailable: Literal["hide", "disable"] = "hide",
) -> ActionState:
    """Normalize the compact availability return forms to :class:`ActionState`."""

    if isinstance(value, ActionState):
        if not value.visible:
            value.enabled = False
        return value
    if value is None or value is True:
        return ActionState()
    if value is False:
        if unavailable == "disable":
            return ActionState(visible=True, enabled=False)
        return ActionState(visible=False, enabled=False)
    raise TypeError("action availability must return bool, ActionState, or None")


async def evaluate_action_state(
    obj: Any,
    *,
    availability_handler: str | None,
    unavailable: Literal["hide", "disable"],
    context: ActionContext,
) -> ActionState:
    """Evaluate one action's optional dynamic availability method."""

    if availability_handler is None:
        return ActionState()
    guard = getattr(obj, availability_handler)
    value = await invoke_action_callable(guard, context)
    return normalize_action_state(value, unavailable=unavailable)


__all__ = [
    "ACTION_METADATA_ATTRIBUTE",
    "EXTRA_FIELD_METADATA_ATTRIBUTE",
    "OVERRIDE_FIELD_METADATA_ATTRIBUTE",
    "ActionContext",
    "ActionMetadata",
    "ActionState",
    "ExtraFieldMetadata",
    "NetworkDeviceMetadata",
    "OverrideFieldMetadata",
    "ReadContext",
    "WriteContext",
    "action",
    "extra_field",
    "evaluate_action_state",
    "get_action_metadata",
    "get_extra_field_metadata",
    "get_override_field_metadata",
    "invoke_action_callable",
    "invoke_read_callable",
    "invoke_write_callable",
    "normalize_action_state",
    "override_field",
    "probe_network_url",
    "resolve_read_data",
    "resolve_write_data",
    "resolve_network_device_status",
]
