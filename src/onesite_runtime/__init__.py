"""Small runtime API shared by OneSite model sources and generated backends.

This package intentionally has no FastAPI, SQLModel, or generator dependency.
``site sync`` copies it into the generated backend so model modules can use the
same action decorators while being introspected and while serving requests.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable, Literal, TypeVar, overload


ACTION_METADATA_ATTRIBUTE = "__onesite_action__"


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


ActionFunction = TypeVar("ActionFunction", bound=Callable[..., Any])


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
    "ActionContext",
    "ActionMetadata",
    "ActionState",
    "action",
    "evaluate_action_state",
    "get_action_metadata",
    "invoke_action_callable",
    "normalize_action_state",
]
