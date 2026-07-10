from pathlib import Path
from typing import Dict

from jinja2 import Environment, FileSystemLoader

from .file_utils import write_file_with_status

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "codegen"


def generate_file(template_name: str, context: Dict, output_path: Path):
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), auto_reload=True)
    template = env.get_template(template_name)
    content = template.render(context)
    write_file_with_status(output_path, content)
