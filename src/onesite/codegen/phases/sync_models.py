"""Phase 2.5 — Model file sync to backend.

Must run after Phase 2 (model table generation) and before Phase 3
(introspection) so that generated + user-defined models are in place
for the Python import step.
"""

from pathlib import Path

from ...project_paths import get_project_paths
from ..file_utils import copy_file_with_status, write_file_with_status
from .base import console

# Root of the onesite package (…/onesite/)
_ONESITE_ROOT = Path(__file__).resolve().parent.parent.parent
_ONESITE_RUNTIME_ROOT = _ONESITE_ROOT.parent / "onesite_runtime"


def phase_sync_models(cwd: Path, backend_path: Path) -> None:
    """Mirror source and built-in models into the generated backend.

    ``backend/app/models`` is generated output, not a second model source.
    Removing obsolete copies before writing prevents deleted project models
    from being imported and regenerated on the next ``site sync``.
    """
    models_src_dir = get_project_paths(cwd).models
    models_dest_dir = backend_path / "app" / "models"
    template_models_dir = _ONESITE_ROOT / "templates" / "models"

    models_dest_dir.mkdir(parents=True, exist_ok=True)
    write_file_with_status(models_dest_dir / "__init__.py", "")

    # Model actions are a runtime concern of the generated application.  Keep
    # their implementation under app.core so the output contains no OneSite
    # package (or package-shaped compatibility shim).
    copy_file_with_status(
        _ONESITE_RUNTIME_ROOT / "__init__.py",
        backend_path / "app" / "core" / "action_runtime.py",
    )

    source_models = (
        {model_file.name: model_file for model_file in models_src_dir.glob("*.py")}
        if models_src_dir.exists()
        else {}
    )
    template_models = (
        {model_file.name: model_file for model_file in template_models_dir.glob("*.py")}
        if template_models_dir.exists()
        else {}
    )

    # Project models override bundled models with the same name.
    desired_models = {**template_models, **source_models}

    for model_file in models_dest_dir.glob("*.py"):
        if model_file.name != "__init__.py" and model_file.name not in desired_models:
            model_file.unlink()
            console.print(f"[yellow]Removed stale generated model {model_file}[/yellow]")

    for name, model_file in sorted(desired_models.items()):
        if name in source_models and name in template_models:
            console.print(f"[dim]Project model {name} overrides the bundled model[/dim]")
        write_file_with_status(
            models_dest_dir / name,
            model_file.read_text(encoding="utf-8"),
        )
