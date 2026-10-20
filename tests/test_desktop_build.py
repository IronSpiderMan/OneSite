"""Coverage for generated Tauri desktop clients."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from onesite.codegen.assets import sync_frontend_assets
from onesite.codegen.config import SiteConfigError, validate_desktop_config
from onesite.codegen.envsync import sync_env_files
from onesite.main import app


def _desktop_project(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path
    (project / "app").mkdir()
    frontend = project / "generated" / "frontend"
    (frontend / "src-tauri").mkdir(parents=True)
    (frontend / "src-tauri" / "tauri.conf.json").write_text("{}", encoding="utf-8")
    (frontend / ".env.desktop").write_text("VITE_DESKTOP=true\n", encoding="utf-8")
    (frontend / "package.json").write_text("{}", encoding="utf-8")
    tauri_cli = frontend / "node_modules" / ".bin" / "tauri"
    tauri_cli.parent.mkdir(parents=True)
    tauri_cli.write_text("", encoding="utf-8")
    (tauri_cli.parent / "tauri.cmd").write_text("", encoding="utf-8")
    return project, frontend


def test_desktop_config_generates_tauri_shell_and_desktop_env(tmp_path):
    config = {"project_name": "Alarm Center", "allowed_origins": []}
    validate_desktop_config(config)

    backend = tmp_path / "generated" / "backend"
    frontend = tmp_path / "generated" / "frontend"
    sync_env_files(config, backend, frontend)
    sync_frontend_assets(tmp_path, config)

    tauri_config = json.loads(
        (frontend / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8")
    )
    package = json.loads((frontend / "package.json").read_text(encoding="utf-8"))
    desktop_env = (frontend / ".env.desktop").read_text(encoding="utf-8")

    assert tauri_config["identifier"] == "com.onesite.alarm-center"
    assert tauri_config["build"]["frontendDist"] == "../dist"
    assert tauri_config["build"]["beforeBuildCommand"] == "npm run build:desktop"
    assert package["scripts"]["tauri"] == "tauri"
    assert package["devDependencies"]["@tauri-apps/cli"].startswith("^2.")
    assert "VITE_DESKTOP=true" in desktop_env
    assert "VITE_API_URL=http://127.0.0.1:8000/api/v1" in desktop_env
    assert (frontend / "src-tauri" / "tauri.macos.conf.json").exists()
    assert (frontend / "src-tauri" / "tauri.windows.conf.json").exists()


def test_desktop_config_rejects_relative_api_url():
    config = {"project_name": "demo", "desktop": {"api_url": "/api/v1"}}

    try:
        validate_desktop_config(config)
    except SiteConfigError as exc:
        assert "absolute http(s) URL" in str(exc)
    else:
        raise AssertionError("relative desktop API URL should be rejected")


@pytest.mark.parametrize(
    ("host_platform", "platform_label"),
    (("darwin", "macOS"), ("win32", "Windows")),
)
def test_desktop_build_targets_only_the_current_platform(
    tmp_path, monkeypatch, host_platform, platform_label
):
    project, frontend = _desktop_project(tmp_path)
    calls = []

    monkeypatch.setattr("onesite.main.get_cwd_safely", lambda: project)
    monkeypatch.setattr("onesite.main.sys.platform", host_platform)
    monkeypatch.setattr("onesite.main._npm_executable", lambda: "/usr/bin/npm")
    monkeypatch.setattr("onesite.main.shutil.which", lambda name: "/usr/bin/cargo")
    monkeypatch.setattr(
        "onesite.main.subprocess.run",
        lambda command, **kwargs: calls.append((command, kwargs)),
    )

    result = CliRunner().invoke(app, ["build", "--component", "desktop"])

    assert result.exit_code == 0, result.output
    assert calls == [
        (
            ["/usr/bin/npm", "run", "tauri", "--", "build"],
            {"cwd": str(frontend), "check": True},
        )
    ]
    assert platform_label in result.output
    assert not (project / "deploy" / "docker-compose.yml").exists()


def test_desktop_build_does_not_attempt_cross_platform_build(tmp_path, monkeypatch):
    project, _ = _desktop_project(tmp_path)
    calls = []
    monkeypatch.setattr("onesite.main.get_cwd_safely", lambda: project)
    monkeypatch.setattr("onesite.main.sys.platform", "linux")
    monkeypatch.setattr(
        "onesite.main.subprocess.run", lambda *args, **kwargs: calls.append(args)
    )

    result = CliRunner().invoke(app, ["build", "--component", "desktop"])

    assert result.exit_code == 1
    assert "macOS and Windows hosts only" in result.output
    assert calls == []
