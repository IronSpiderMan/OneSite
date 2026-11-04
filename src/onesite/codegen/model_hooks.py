"""Discover project-owned model hooks without importing business code."""

from __future__ import annotations

import ast
from pathlib import Path
from pprint import pformat

from ..project_paths import get_project_paths
from .file_utils import mirror_source_tree, write_file_with_status
from .types import ModelDefinition


# The model-method and external-function APIs differ only in their target argument.
INSTANCE_HOOK_ARGUMENTS = {
    "on_before_create": {"session", "context"},
    "on_after_create": {"session", "context"},
    "on_before_update": {"session", "old", "changes", "context"},
    "on_after_update": {"session", "old", "changes", "context"},
    "on_before_delete": {"session", "old", "context"},
    "on_after_delete": {"session", "old", "context"},
    "on_after_commit_create": {"context"},
    "on_after_commit_update": {"old", "changes", "context"},
    "on_after_commit_delete": {"old", "context"},
}
BULK_HOOK_ARGUMENTS = {
    "on_after_bulk_delete": {"session", "olds", "context"},
    "on_after_commit_bulk_delete": {"olds", "context"},
}
UPDATE_HOOKS = {"on_before_update", "on_after_update", "on_after_commit_update"}


def _validate_hook(path: Path, function: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
    name = function.name
    if name in INSTANCE_HOOK_ARGUMENTS:
        supported = INSTANCE_HOOK_ARGUMENTS[name] | {"obj"}
    elif name in BULK_HOOK_ARGUMENTS:
        supported = BULK_HOOK_ARGUMENTS[name] | {"model"}
    else:
        raise ValueError(f"{path}:{function.lineno}: unknown model hook '{name}'")

    arguments = function.args
    if arguments.posonlyargs:
        raise ValueError(
            f"{path}:{function.lineno}: {name} parameter "
            f"'{arguments.posonlyargs[0].arg}' cannot be positional-only"
        )
    required = arguments.args[: len(arguments.args) - len(arguments.defaults)]
    required += [
        argument for argument, default in zip(arguments.kwonlyargs, arguments.kw_defaults)
        if default is None
    ]
    for argument in required:
        if argument.arg not in supported:
            expected = ", ".join(sorted(supported))
            raise ValueError(
                f"{path}:{function.lineno}: {name} has unsupported required "
                f"parameter '{argument.arg}'. Supported parameters: {expected}"
            )


def sync_model_hooks(cwd: Path, backend_path: Path, models: list[ModelDefinition]) -> None:
    """Validate, bind and mirror ``app/hooks/<model_key>.py`` into the backend.

    Private modules and packages may hold helpers; only public Python modules
    directly under ``app/hooks`` are model hook entry points. Bindings use the
    introspected class identity, independently of its table or source filename.
    """
    source = get_project_paths(cwd).source / "hooks"
    destination = backend_path / "app" / "hooks"
    by_key = {model["module_name"]: model for model in models}
    registry: dict[tuple[str, str], dict[str, str]] = {}
    update_models: list[ModelDefinition] = []

    for path in sorted(source.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            compile(tree, str(path), "exec")
        except (SyntaxError, UnicodeError) as exc:
            raise ValueError(f"Unable to parse model hooks {path}: {exc}") from exc
        if path.parent != source or path.stem.startswith("_"):
            continue

        model = by_key.get(path.stem)
        if model is None:
            available = ", ".join(sorted(by_key)) or "(none)"
            raise ValueError(
                f"{path}: unknown hook target model '{path.stem}'. "
                f"Available model keys: {available}. Enable the model's plugin if needed; "
                "prefix helper modules with '_'."
            )
        if model.get("frontend_only") or (
            model.get("is_link_table") and not model.get("is_association_table")
        ):
            raise ValueError(f"{path}: model '{path.stem}' has no generated CUD lifecycle")

        hooks: dict[str, str] = {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("on_"):
                    continue
                _validate_hook(path, node)
                if node.name in hooks:
                    raise ValueError(f"{path}:{node.lineno}: duplicate model hook '{node.name}'")
                hooks[node.name] = f"app.hooks.{path.stem}"
            elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Assign):
                    names = [target.id for target in node.targets if isinstance(target, ast.Name)]
                elif isinstance(node, ast.AnnAssign):
                    names = [node.target.id] if isinstance(node.target, ast.Name) else []
                else:
                    names = [alias.asname or alias.name.split(".")[0] for alias in node.names]
                for name in names:
                    if name.startswith("on_"):
                        raise ValueError(
                            f"{path}:{node.lineno}: model hook '{name}' must be defined "
                            "as a top-level function"
                        )
        if hooks:
            identity = (f"app.models.{model['source_module']}", model["name"])
            registry[identity] = hooks
            if UPDATE_HOOKS.intersection(hooks):
                update_models.append(model)

    # Finish all validation before changing metadata or generated artifacts.
    mirror_source_tree(source, destination, "model hooks")
    if source.exists() and not (destination / "__init__.py").exists():
        write_file_with_status(destination / "__init__.py", "")
    write_file_with_status(
        backend_path / "app" / "core" / "model_hook_registry.py",
        '"""Generated model hook bindings; edit app/hooks in the project source."""\n\n'
        f"MODEL_HOOKS = {pformat(registry, sort_dicts=True)}\n",
    )
    for model in update_models:
        model["has_update_hooks"] = True
