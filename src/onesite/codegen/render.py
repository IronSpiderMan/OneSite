from pathlib import Path
from typing import Dict

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PrefixLoader

from .file_utils import write_file_with_status

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "codegen"
THEME_TEMPLATE_DIR = TEMPLATE_DIR / "themes"


def create_template_environment(theme_name: str | None = None) -> Environment:
    """Create a Jinja environment with optional theme overrides.

    Theme templates are resolved before the shared templates.  The ``common/``
    prefix always points at the shared template root, which lets a compact theme
    wrapper set layout variables and then include the full shared implementation
    without copying its data-fetching and form logic.
    """
    shared_loader = FileSystemLoader(str(TEMPLATE_DIR))
    loaders = []
    if theme_name:
        theme_path = THEME_TEMPLATE_DIR / theme_name
        if theme_path.is_dir():
            loaders.append(FileSystemLoader(str(theme_path)))
    loaders.extend(
        [
            PrefixLoader({"common": shared_loader}),
            shared_loader,
        ]
    )
    return Environment(loader=ChoiceLoader(loaders), auto_reload=True)


def generate_file(template_name: str, context: Dict, output_path: Path):
    env = create_template_environment()
    template = env.get_template(template_name)
    content = template.render(context)
    write_file_with_status(output_path, content)


def generate_file_if_missing(template_name: str, context: Dict, output_path: Path):
    """Render a file only once, preserving developer-owned implementations."""
    if output_path.exists():
        return
    generate_file(template_name, context, output_path)


def generate_theme_file(
    template_name: str,
    context: Dict,
    output_path: Path,
    theme_name: str,
):
    """Render a frontend template using a theme override when available."""
    env = create_template_environment(theme_name)
    template = env.get_template(template_name)
    themed_context = {**context, "codegen_theme": theme_name}
    content = template.render(themed_context)
    write_file_with_status(output_path, content)
