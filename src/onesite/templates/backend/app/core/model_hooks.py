"""Helpers for invoking model-level CUD lifecycle hooks."""

from __future__ import annotations

import inspect
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class ModelHookContext:
    """Context shared by transactional and after-commit model hooks."""

    operation: Literal["create", "update", "delete"]
    input_data: dict[str, Any] = field(default_factory=dict)
    changed_fields: frozenset[str] = field(default_factory=frozenset)


def snapshot_model(target: Any) -> dict[str, Any]:
    """Capture mapped column values without relationship traversal."""

    return {
        column.name: deepcopy(getattr(target, column.name))
        for column in target.__table__.columns
    }


async def invoke_model_hook(target: Any, hook_name: str, **values: Any) -> None:
    """Invoke a hook with the supported arguments it declares.

    Hooks may be regular or async instance methods. Arguments are matched by
    name so a hook only needs to declare the values it uses, for example
    ``async def on_after_update(self, session, old, context)``.
    """

    hook = getattr(target, hook_name, None)
    if hook is None:
        return

    signature = inspect.signature(hook)
    kwargs: dict[str, Any] = {}
    for name, parameter in signature.parameters.items():
        if name in values:
            kwargs[name] = values[name]
        elif (
            parameter.default is inspect.Parameter.empty
            and parameter.kind
            not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        ):
            supported = ", ".join(sorted(values))
            raise TypeError(
                f"{type(target).__name__}.{hook_name} has unsupported required "
                f"parameter '{name}'. Supported parameters: {supported}"
            )

    result = hook(**kwargs)
    if inspect.isawaitable(result):
        await result
