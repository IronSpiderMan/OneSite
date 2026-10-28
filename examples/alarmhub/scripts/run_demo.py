"""Run the mock OPC UA server, generated API and frontend together."""

import os
import json
import signal
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def main():
    backend = PROJECT / "generated/backend"
    frontend = PROJECT / "generated/frontend"
    npm = shutil.which("npm")
    if (
        not (backend / "app/main.py").exists()
        or not (frontend / "node_modules").exists()
        or not npm
    ):
        raise SystemExit(
            "Run site sync --install in examples/alarmhub first (Node.js/npm required)."
        )
    commands = [
        ([sys.executable, str(PROJECT / "scripts/mock_opcua.py")], PROJECT, {}),
        (
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "18280",
            ],
            backend,
            {},
        ),
        (
            [npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", "15273"],
            frontend,
            {"VITE_API_URL": "http://127.0.0.1:18280/api/v1"},
        ),
    ]
    runtime_config = frontend / "public/config.js"
    original_config = runtime_config.read_bytes() if runtime_config.exists() else None
    runtime_config.write_text(
        "window.__ENV__ = "
        + json.dumps(
            {
                "API_URL": "http://127.0.0.1:18280/api/v1",
                "PROJECT_NAME": "AlarmHub OPC UA Demo",
                "NODE_ENV": "development",
            }
        )
        + ";\n"
    )
    children = []
    try:
        for command, cwd, extra in commands:
            children.append(
                subprocess.Popen(
                    command, cwd=cwd, env={**os.environ, **extra}, start_new_session=True
                )
            )
        print("\nAlarmHub demo: http://127.0.0.1:15273", flush=True)
        print(
            "API: http://127.0.0.1:18280/docs | OPC UA: opc.tcp://127.0.0.1:14860/alarmhub/",
            flush=True,
        )
        print("Press Ctrl+C to stop all demo processes.\n", flush=True)
        while True:
            for child in children:
                if child.poll() is not None:
                    raise SystemExit(
                        f"Demo process exited ({child.returncode}); check its output above."
                    )
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for child in children:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        if original_config is None:
            runtime_config.unlink(missing_ok=True)
        else:
            runtime_config.write_bytes(original_config)


if __name__ == "__main__":
    main()
