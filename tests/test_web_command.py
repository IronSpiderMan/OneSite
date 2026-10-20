"""CLI entry point for the separately maintained, bundled WebUI."""

from pathlib import Path
import sys

from typer.testing import CliRunner

from onesite import main


def test_web_preserves_interpreter_working_directory_and_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = []
    monkeypatch.setattr(main.os, "execv", lambda *args: calls.append((args, Path.cwd())))

    result = CliRunner().invoke(main.app, ["web"])

    assert result.exit_code == 0, result.output
    (python, argv), cwd = calls[0]
    assert python == argv[0] == sys.executable
    assert Path(argv[1]) == Path(main.__file__).resolve().parents[2] / "webui.py"
    assert argv[2:] == ["--port", "8765"]
    assert cwd == tmp_path


def test_web_forwards_editor_options_without_shell_interpretation(monkeypatch):
    calls = []
    monkeypatch.setattr(main.os, "execv", lambda *args: calls.append(args))
    result = CliRunner().invoke(
        main.app,
        [
            "web",
            "--port",
            "9000",
            "--projects-dir",
            "work space/projects",
            "--python",
            "custom env/bin/python",
            "--no-browser",
        ],
    )
    assert result.exit_code == 0, result.output
    assert calls[0][1][2:] == [
        "--port",
        "9000",
        "--projects-dir",
        "work space/projects",
        "--python",
        "custom env/bin/python",
        "--no-browser",
    ]


def test_web_prefers_bundled_file_when_installed(tmp_path, monkeypatch):
    package = tmp_path / "onesite"
    package.mkdir()
    bundled = package / "_webui.py"
    bundled.write_text("# packaged editor\n")
    monkeypatch.setattr(main, "__file__", str(package / "main.py"))
    assert main._webui_script() == bundled


def test_web_help_does_not_load_or_start_editor(monkeypatch):
    def fail():
        raise AssertionError("help must not start the server")

    monkeypatch.setattr(main, "_webui_script", fail)
    result = CliRunner().invoke(main.app, ["web", "--help"])
    assert result.exit_code == 0
    for option in ("--port", "--projects-dir", "--python", "--no-browser"):
        assert option in result.output


def test_web_reports_launch_failure(monkeypatch):
    def fail(*args):
        raise OSError("test launch failure")

    monkeypatch.setattr(main.os, "execv", fail)
    result = CliRunner().invoke(main.app, ["web"])
    assert result.exit_code == 1
    assert "Unable to start WebUI" in result.output
    assert "test launch failure" in result.output


def test_web_rejects_invalid_port(monkeypatch):
    def fail(*args):
        raise AssertionError("invalid options must not launch a server")

    monkeypatch.setattr(main.os, "execv", fail)
    result = CliRunner().invoke(main.app, ["web", "--port", "65536"])
    assert result.exit_code == 2


def test_web_forwards_project_path(monkeypatch):
    calls = []
    monkeypatch.setattr(main.os, "execv", lambda *args: calls.append(args))
    for path in ("Demo", ".", "/tmp/project with spaces"):
        result = CliRunner().invoke(main.app, ["web", path, "--no-browser"])
        assert result.exit_code == 0, result.output
        assert calls[-1][1][-2:] == ["--", path]
