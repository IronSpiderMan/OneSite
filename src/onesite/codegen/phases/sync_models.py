"""Phase 2.5 — Model file sync to backend.

Must run after Phase 2 (model table generation) and before Phase 3
(introspection) so that generated + user-defined models are in place
for the Python import step.
"""

import shutil
from pathlib import Path

from .base import console

# Root of the onesite package (…/onesite/)
_ONESITE_ROOT = Path(__file__).resolve().parent.parent.parent


def phase_sync_models(cwd: Path, backend_path: Path) -> None:
    """Copy model .py files from *project* models/ and *template* models/ into backend."""
    models_src_dir = cwd / "models"
    models_dest_dir = backend_path / "app" / "models"
    template_models_dir = _ONESITE_ROOT / "templates" / "models"

    models_dest_dir.mkdir(parents=True, exist_ok=True)
    (models_dest_dir / "__init__.py").touch(exist_ok=True)

    if models_src_dir.exists():
        console.print(
            f"[green]Syncing models from {models_src_dir} to {models_dest_dir}...[/green]"
        )
        for model_file in models_src_dir.glob("*.py"):
            shutil.copy2(model_file, models_dest_dir / model_file.name)
            console.print(f"Synced model: {model_file.name}")

    if template_models_dir.exists():
        for model_file in template_models_dir.glob("*.py"):
            target_in_project = models_src_dir / model_file.name
            if not target_in_project.exists():
                shutil.copy2(model_file, models_dest_dir / model_file.name)
                console.print(
                    f"Synced base model from template: {model_file.name}"
                )
            else:
                console.print(
                    f"Skipping template model {model_file.name} (overridden in project)"
                )
