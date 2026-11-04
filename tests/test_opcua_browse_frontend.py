"""Execute the generated BrowsePanel against controlled discovery and CRUD services."""

import shutil
import subprocess
from pathlib import Path

import pytest

from onesite.codegen.render import create_template_environment


def test_browse_panel_imports_all_conditions_and_preserves_retry_selection(tmp_path):
    root = Path(__file__).resolve().parents[1]
    node = shutil.which("node")
    compilers = list(root.glob("examples/*/frontend/node_modules/typescript/lib/typescript.js"))
    if not node or not compilers:
        pytest.skip("Node and a local TypeScript compiler are required")
    panel = tmp_path / "BrowsePanel.tsx"
    panel.write_text(
        create_template_environment().get_template("opcua_browse_panel.tsx.j2").render()
    )
    checked = subprocess.run(
        [node, str(root / "tests/support/check_opcua_browse_frontend.cjs"),
         str(compilers[0]), str(panel)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert checked.returncode == 0, checked.stdout + checked.stderr
