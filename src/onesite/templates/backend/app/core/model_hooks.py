"""Helpers for invoking model-level CUD lifecycle hooks."""

from __future__ import annotations

import inspect
import logging
from copy import deepcopy
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import import_module
from typing import Any, Literal


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelHookContext:
    """Context shared by transactional and after-commit model hooks."""

    operation: Literal["create", "update", "delete", "bulk_delete"]
    input_data: dict[str, Any] = field(default_factory=dict)
    changed_fields: frozenset[str] = field(default_factory=frozenset)


def snapshot_model(target: Any) -> dict[str, Any]:
    """Capture mapped column values without relationship traversal."""

    return {
        column.name: deepcopy(getattr(target, column.name))
        for column in target.__table__.columns
    }


async def _invoke_named_hook(hook: Any, label: str, values: dict[str, Any]) -> None:
    signature = inspect.signature(hook)
    kwargs: dict[str, Any] = {}
    for name, parameter in signature.parameters.items():
        if parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        if parameter.kind is inspect.Parameter.POSITIONAL_ONLY:
            raise TypeError(f"{label} parameter '{name}' cannot be positional-only")
        if name in values:
            kwargs[name] = values[name]
        elif parameter.default is inspect.Parameter.empty:
            supported = ", ".join(sorted(values))
            raise TypeError(
                f"{label} has unsupported required parameter '{name}'. "
                f"Supported parameters: {supported}"
            )
    result = hook(**kwargs)
    if inspect.isawaitable(result):
        await result


async def _invoke_model_method(target: Any, hook_name: str, values: dict[str, Any]) -> None:
    hook = getattr(target, hook_name, None)
    if hook is not None:
        model = target if inspect.isclass(target) else type(target)
        await _invoke_named_hook(hook, f"{model.__name__}.{hook_name}", values)


@lru_cache(maxsize=None)
def _load_external_hook(module_name: str, hook_name: str) -> Any:
    hook = getattr(import_module(module_name), hook_name)
    if not callable(hook):
        raise TypeError(f"{module_name}.{hook_name} must be callable")
    return hook


async def _invoke_external_hook(target: Any, hook_name: str, values: dict[str, Any]) -> None:
    try:
        from app.core.model_hook_registry import MODEL_HOOKS
    except ModuleNotFoundError as exc:
        if exc.name not in {"app", "app.core", "app.core.model_hook_registry"}:
            raise
        return

    model = target if inspect.isclass(target) else type(target)
    module_name = MODEL_HOOKS.get((model.__module__, model.__name__), {}).get(hook_name)
    if module_name is not None:
        hook = _load_external_hook(module_name, hook_name)
        argument = "model" if inspect.isclass(target) else "obj"
        await _invoke_named_hook(
            hook, f"{module_name}.{hook_name}", {**values, argument: target}
        )


async def invoke_model_hook(target: Any, hook_name: str, **values: Any) -> None:
    """Run model methods and external functions at the same lifecycle boundary.

    Before hooks run external functions first so model validators see their
    changes. After hooks run model methods first so external functions see the
    initialized state. Arguments are injected by name; sync and async work alike.
    Transactional failures propagate. Post-commit failures are logged separately
    so a failed model method does not suppress the external function.
    """
    handlers = (_invoke_model_method, _invoke_external_hook)
    if hook_name.startswith("on_before_"):
        handlers = tuple(reversed(handlers))
    for handler in handlers:
        try:
            await handler(target, hook_name, values)
        except Exception:
            if not hook_name.startswith("on_after_commit_"):
                raise
            model = target if inspect.isclass(target) else type(target)
            logger.exception(
                "Post-commit hook %s.%s failed (%s)",
                model.__name__, hook_name, handler.__name__,
            )

    # External resources behave like framework-owned transactional on_after
    # hooks. The import stays lazy so ordinary projects need no runtime module.
    operation = {
        "on_after_create": "create",
        "on_after_update": "update",
        "on_after_delete": "delete",
    }.get(hook_name)
    if operation is not None and "session" in values:
        try:
            from app.core.external_resources import sync_external_resource_change
        except ModuleNotFoundError as exc:
            if exc.name not in {"app", "app.core", "app.core.external_resources"}:
                raise
        else:
            await sync_external_resource_change(
                values["session"],
                target=target,
                operation=operation,
                previous=values.get("old"),
            )
