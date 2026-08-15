"""Optional helpers for callers that manage a local MediaMTX process themselves.

The ``site run`` command deliberately does not invoke these helpers.
"""

from __future__ import annotations

import hashlib
import http.client
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from tarfile import open as open_tar


MEDIAMTX_VERSION = "1.19.3"
_RELEASE_ROOT = "https://github.com/bluenviron/mediamtx/releases/download"


class MediaMTXError(RuntimeError):
    """Raised when MediaMTX cannot be installed or started."""


@dataclass
class MediaMTXProcess:
    """A MediaMTX instance, which may be owned by another process."""

    process: subprocess.Popen[bytes] | None = None

    @property
    def owned(self) -> bool:
        return self.process is not None

    def stop(self) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)


def _cache_root() -> Path:
    override = os.environ.get("ONESITE_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "onesite"
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "onesite" / "Cache"
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "onesite"


def _release_asset() -> tuple[str, str]:
    system = platform.system().lower()
    systems = {"darwin": "darwin", "linux": "linux", "windows": "windows"}
    if system not in systems:
        raise MediaMTXError(f"MediaMTX is not supported on {platform.system() or sys.platform}.")

    machine = platform.machine().lower()
    architectures = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
        "armv7l": "armv7",
        "armv6l": "armv6",
    }
    architecture = architectures.get(machine)
    if architecture is None:
        raise MediaMTXError(f"MediaMTX has no supported binary for architecture {machine!r}.")

    extension = "zip" if system == "windows" else "tar.gz"
    filename = f"mediamtx_v{MEDIAMTX_VERSION}_{systems[system]}_{architecture}.{extension}"
    return filename, "mediamtx.exe" if system == "windows" else "mediamtx"


def mediamtx_binary_path() -> Path:
    """Return the versioned executable path in OneSite's user cache."""
    _, executable = _release_asset()
    return _cache_root() / "mediamtx" / f"v{MEDIAMTX_VERSION}" / executable


def _download(url: str, destination: Path) -> None:
    # Local media infrastructure must not accidentally use a stale corporate
    # proxy from HTTP_PROXY/HTTPS_PROXY. GitHub redirects are still followed.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(url, headers={"User-Agent": "OneSiteTool"})
    try:
        with opener.open(request, timeout=60) as response, destination.open("wb") as output:
            shutil.copyfileobj(response, output)
    except (OSError, urllib.error.URLError) as exc:
        raise MediaMTXError(f"Unable to download {url}: {exc}") from exc


def _expected_checksum(checksums: Path, asset_name: str) -> str:
    for line in checksums.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == asset_name:
            return parts[0].lower()
    raise MediaMTXError(f"Official checksum for {asset_name} was not found.")


def _extract_executable(archive: Path, executable_name: str, destination: Path) -> None:
    extracted = destination.with_name(destination.name + ".tmp")
    try:
        if archive.name.endswith(".zip"):
            with zipfile.ZipFile(archive) as bundle:
                member = next(
                    (name for name in bundle.namelist() if Path(name).name == executable_name),
                    None,
                )
                if member is None:
                    raise MediaMTXError(f"{executable_name} is missing from the MediaMTX archive.")
                with bundle.open(member) as source, extracted.open("wb") as output:
                    shutil.copyfileobj(source, output)
        else:
            with open_tar(archive, mode="r:gz") as bundle:
                member = next(
                    (item for item in bundle.getmembers() if Path(item.name).name == executable_name and item.isfile()),
                    None,
                )
                if member is None:
                    raise MediaMTXError(f"{executable_name} is missing from the MediaMTX archive.")
                source = bundle.extractfile(member)
                if source is None:
                    raise MediaMTXError(f"Unable to read {executable_name} from the MediaMTX archive.")
                with source, extracted.open("wb") as output:
                    shutil.copyfileobj(source, output)
        if os.name != "nt":
            extracted.chmod(0o755)
        extracted.replace(destination)
    finally:
        extracted.unlink(missing_ok=True)


def ensure_mediamtx_installed() -> Path:
    """Download and checksum the current platform binary when it is absent."""
    destination = mediamtx_binary_path()
    if destination.is_file() and (os.name == "nt" or os.access(destination, os.X_OK)):
        return destination

    asset_name, executable_name = _release_asset()
    destination.parent.mkdir(parents=True, exist_ok=True)
    release_url = f"{_RELEASE_ROOT}/v{MEDIAMTX_VERSION}"
    with tempfile.TemporaryDirectory(prefix="onesite-mediamtx-") as temp_dir:
        temporary = Path(temp_dir)
        archive = temporary / asset_name
        checksums = temporary / "checksums.sha256"
        _download(f"{release_url}/{asset_name}", archive)
        _download(f"{release_url}/checksums.sha256", checksums)

        expected = _expected_checksum(checksums, asset_name)
        actual = hashlib.sha256(archive.read_bytes()).hexdigest()
        if actual != expected:
            raise MediaMTXError(
                f"Checksum verification failed for {asset_name}; the downloaded file was discarded."
            )
        _extract_executable(archive, executable_name, destination)
    return destination


def _api_is_ready(host: str = "127.0.0.1", port: int = 9997) -> bool:
    connection = http.client.HTTPConnection(host, port, timeout=0.25)
    try:
        connection.request("GET", "/v3/info")
        response = connection.getresponse()
        response.read()
        return response.status == 200
    except (OSError, http.client.HTTPException):
        return False
    finally:
        connection.close()


def start_mediamtx() -> MediaMTXProcess:
    """Start MediaMTX for local HLS previews, or reuse an existing instance."""
    if _api_is_ready():
        return MediaMTXProcess()

    executable = ensure_mediamtx_installed()
    configuration = executable.parent / "onesite.yml"
    if not configuration.exists():
        configuration.write_text("{}\n", encoding="utf-8")
    environment = os.environ.copy()
    environment.update(
        {
            "MTX_API": "yes",
            "MTX_APIADDRESS": "127.0.0.1:9997",
            "MTX_HLS": "yes",
            "MTX_HLSADDRESS": "127.0.0.1:8888",
            "MTX_HLSALLOWORIGINS": "*",
            "MTX_HLSVARIANT": "fmp4",
            # The local runner is only a pull gateway. Disable unrelated
            # listeners to avoid claiming common RTSP/RTMP/WebRTC/SRT ports.
            "MTX_RTSP": "no",
            "MTX_RTMP": "no",
            "MTX_WEBRTC": "no",
            "MTX_SRT": "no",
            "MTX_MOQ": "no",
        }
    )
    try:
        process = subprocess.Popen([str(executable), str(configuration)], env=environment)
    except OSError as exc:
        raise MediaMTXError(f"Unable to start MediaMTX: {exc}") from exc

    for _ in range(100):
        if _api_is_ready():
            return MediaMTXProcess(process)
        exit_code = process.poll()
        if exit_code is not None:
            raise MediaMTXError(f"MediaMTX exited during startup with status {exit_code}.")
        time.sleep(0.1)

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
    raise MediaMTXError("MediaMTX did not open its control API at 127.0.0.1:9997.")
