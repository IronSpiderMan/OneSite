"""Command project build coverage."""

import os

import pytest
from typer.testing import CliRunner

from onesite.cmd_build import CommandBuildError, build_command_projects
from onesite.main import app


pytestmark = pytest.mark.skipif(os.name == "nt", reason="POSIX build script tests")


def test_builds_projects_and_copies_same_named_executable(tmp_path):
    project = tmp_path / "app" / "cmd" / "reporter"
    project.mkdir(parents=True)
    (project / "build.sh").write_text(
        "#!/bin/sh\n"
        "printf '#!/bin/sh\\necho report\\n' > reporter\n"
        "chmod +x reporter\n",
        encoding="utf-8",
    )

    copied = build_command_projects(tmp_path)

    destination = tmp_path / "generated" / "backend" / "bin" / "reporter"
    assert copied == [destination]
    assert destination.exists()
    assert os.access(destination, os.X_OK)


def test_skips_projects_without_platform_build_script(tmp_path):
    project = tmp_path / "app" / "cmd" / "windows_only"
    project.mkdir(parents=True)
    (project / "build.bat").write_text("echo build\n", encoding="utf-8")

    assert build_command_projects(tmp_path) == []
    assert not (tmp_path / "generated" / "backend" / "bin").exists()


def test_fails_when_build_does_not_create_same_named_executable(tmp_path):
    project = tmp_path / "app" / "cmd" / "missing_output"
    project.mkdir(parents=True)
    (project / "build.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")

    with pytest.raises(CommandBuildError, match="did not produce"):
        build_command_projects(tmp_path)


def test_sync_only_builds_command_projects_when_flag_is_set(tmp_path, monkeypatch):
    calls: list[object] = []
    monkeypatch.setattr("onesite.main.get_cwd_safely", lambda: tmp_path)
    monkeypatch.setattr("onesite.main._ensure_deploy_files", lambda root: root / "deploy")
    monkeypatch.setattr("onesite.generator.generate_code", lambda: calls.append("sync"))
    monkeypatch.setattr(
        "onesite.cmd_build.build_command_projects",
        lambda root: calls.append(root) or [],
    )
    runner = CliRunner()

    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0, result.output
    assert calls == ["sync"]

    calls.clear()
    result = runner.invoke(app, ["sync", "--build-cmd"])
    assert result.exit_code == 0, result.output
    assert calls == ["sync", tmp_path]
