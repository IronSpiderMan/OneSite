from pathlib import Path
from typing import Any, Dict

from rich.console import Console

console = Console()


def load_site_config(cwd: Path) -> Dict[str, Any]:
    config_path = cwd / "site_config.json"
    if config_path.exists():
        import json

        try:
            return json.loads(config_path.read_text())
        except Exception as e:
            console.print(f"[red]Error loading site_config.json: {e}[/red]")
    return {}

