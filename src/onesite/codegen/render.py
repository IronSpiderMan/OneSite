from pathlib import Path
from typing import Dict

from jinja2 import Environment, FileSystemLoader
from rich.console import Console

console = Console()

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "codegen"


def generate_file(template_name: str, context: Dict, output_path: Path):
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template(template_name)
    content = template.render(context)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    console.print(f"Generated {output_path}")
