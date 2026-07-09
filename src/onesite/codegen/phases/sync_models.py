"""Phase 2.5 — Model file sync to backend.

Must run after Phase 2 (model table generation) and before Phase 3
(introspection) so that generated + user-defined models are in place
for the Python import step.
"""

from pathlib import Path

from ..file_utils import copy_file_with_status, write_file_with_status
from .base import console

# Root of the onesite package (…/onesite/)
_ONESITE_ROOT = Path(__file__).resolve().parent.parent.parent


def phase_sync_models(cwd: Path, backend_path: Path) -> None:
    """Copy model .py files from *project* models/ and *template* models/ into backend."""
    models_src_dir = cwd / "models"
    models_dest_dir = backend_path / "app" / "models"
    template_models_dir = _ONESITE_ROOT / "templates" / "models"

    models_dest_dir.mkdir(parents=True, exist_ok=True)
    write_file_with_status(models_dest_dir / "__init__.py", "")

    if models_src_dir.exists():
        for model_file in models_src_dir.glob("*.py"):
            copy_file_with_status(model_file, models_dest_dir / model_file.name)

    if template_models_dir.exists():
        for model_file in template_models_dir.glob("*.py"):
            target_in_project = models_src_dir / model_file.name
            if not target_in_project.exists():
                copy_file_with_status(model_file, models_dest_dir / model_file.name)
            else:
                console.print(
                    f"[dim]Skipping template model {model_file.name} (overridden in project)[/dim]"
                )
