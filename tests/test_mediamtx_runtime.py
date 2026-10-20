import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from onesite import mediamtx_runtime
from onesite.main import app


def test_release_asset_maps_macos_arm(monkeypatch):
    monkeypatch.setattr(mediamtx_runtime.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(mediamtx_runtime.platform, "machine", lambda: "arm64")

    asset, executable = mediamtx_runtime._release_asset()

    assert asset == "mediamtx_v1.19.3_darwin_arm64.tar.gz"
    assert executable == "mediamtx"


def test_ensure_installed_checks_and_extracts_archive(tmp_path, monkeypatch):
    monkeypatch.setenv("ONESITE_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(mediamtx_runtime.platform, "system", lambda: "Linux")
    monkeypatch.setattr(mediamtx_runtime.platform, "machine", lambda: "x86_64")
    executable_data = b"fake mediamtx executable"

    def fake_download(url: str, destination: Path) -> None:
        if destination.name == "checksums.sha256":
            asset = "mediamtx_v1.19.3_linux_amd64.tar.gz"
            archive = destination.parent / asset
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            destination.write_text(f"{digest}  {asset}\n", encoding="utf-8")
            return
        with tarfile.open(destination, "w:gz") as bundle:
            info = tarfile.TarInfo("mediamtx")
            info.size = len(executable_data)
            bundle.addfile(info, io.BytesIO(executable_data))

    monkeypatch.setattr(mediamtx_runtime, "_download", fake_download)

    binary = mediamtx_runtime.ensure_mediamtx_installed()

    assert binary.read_bytes() == executable_data
    assert binary.stat().st_mode & 0o100


def test_start_reuses_existing_instance_without_download(monkeypatch):
    monkeypatch.setattr(mediamtx_runtime, "_api_is_ready", lambda: True)
    monkeypatch.setattr(
        mediamtx_runtime,
        "ensure_mediamtx_installed",
        lambda: pytest.fail("download should not be attempted"),
    )

    runtime = mediamtx_runtime.start_mediamtx()

    assert runtime.owned is False


def test_owned_process_is_terminated():
    class FakeProcess:
        def __init__(self):
            self.terminated = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

        def wait(self, timeout):
            return 0

    process = FakeProcess()
    runtime = mediamtx_runtime.MediaMTXProcess(process)  # type: ignore[arg-type]

    runtime.stop()

    assert process.terminated is True


def test_site_run_backend_never_manages_mediamtx(tmp_path, monkeypatch):
    backend = tmp_path / "generated" / "backend"
    backend.mkdir(parents=True)
    (tmp_path / "site_config.json").write_text(
        json.dumps(
            {
                "video_stream": {
                    "rtsp": {"enabled": True, "allowed_hosts": ["192.168.1.14"]}
                }
            }
        ),
        encoding="utf-8",
    )

    calls = []
    monkeypatch.setattr(
        mediamtx_runtime,
        "start_mediamtx",
        lambda: pytest.fail("MediaMTX should not be started or downloaded"),
    )
    monkeypatch.setattr("onesite.main.subprocess.run", lambda *args, **kwargs: calls.append((args, kwargs)))

    result = CliRunner().invoke(app, ["run", str(tmp_path), "--component", "backend"])

    assert result.exit_code == 0, result.output
    assert calls[0][0][0] == ["uvicorn", "app.main:app", "--reload"]


def test_site_run_backend_skips_mediamtx_when_rtsp_is_disabled(tmp_path, monkeypatch):
    backend = tmp_path / "generated" / "backend"
    backend.mkdir(parents=True)
    (tmp_path / "site_config.json").write_text(
        json.dumps({"video_stream": {"rtsp": {"enabled": False}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        mediamtx_runtime,
        "start_mediamtx",
        lambda: pytest.fail("MediaMTX should not be started or downloaded"),
    )
    calls = []
    monkeypatch.setattr(
        "onesite.main.subprocess.run", lambda *args, **kwargs: calls.append((args, kwargs))
    )

    result = CliRunner().invoke(app, ["run", str(tmp_path), "--component", "backend"])

    assert result.exit_code == 0, result.output
    assert calls[0][0][0] == ["uvicorn", "app.main:app", "--reload"]


def test_site_run_passes_host_to_backend(tmp_path, monkeypatch):
    backend = tmp_path / "generated" / "backend"
    backend.mkdir(parents=True)
    (tmp_path / "site_config.json").write_text("{}", encoding="utf-8")
    calls = []
    monkeypatch.setattr(
        "onesite.main.subprocess.run", lambda *args, **kwargs: calls.append((args, kwargs))
    )

    result = CliRunner().invoke(
        app, ["run", str(tmp_path), "--component", "backend", "--host", "0.0.0.0"]
    )

    assert result.exit_code == 0, result.output
    assert calls[0][0][0] == [
        "uvicorn",
        "app.main:app",
        "--reload",
        "--host",
        "0.0.0.0",
    ]


def test_site_run_passes_host_to_frontend(tmp_path, monkeypatch):
    frontend = tmp_path / "generated" / "frontend"
    (frontend / "node_modules").mkdir(parents=True)
    (frontend / "package.json").write_text("{}", encoding="utf-8")
    calls = []
    monkeypatch.setattr("onesite.main._npm_executable", lambda: "npm")
    monkeypatch.setattr(
        "onesite.main.subprocess.run", lambda *args, **kwargs: calls.append((args, kwargs))
    )

    result = CliRunner().invoke(
        app, ["run", str(tmp_path), "--component", "frontend", "--host", "0.0.0.0"]
    )

    assert result.exit_code == 0, result.output
    assert calls[0][0][0] == ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
