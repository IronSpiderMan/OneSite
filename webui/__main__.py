"""OneSite Studio 入口点.

支持作为模块运行：python -m webui
"""

from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path

from .src.exceptions import EditorError
from .src.handler import Handler
from .src.studio import Studio


def main() -> None:
    """主入口函数.

    解析命令行参数，启动Studio和HTTP服务器。
    """
    parser = argparse.ArgumentParser(
        description="OneSite Studio: independent, local project editor and CLI supervisor.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "project",
        nargs="?",
        type=Path,
        help="Open project path, creating it if missing",
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--projects-dir", type=Path, default=Path.cwd() / "projects")
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable with OneSite installed",
    )
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    studio = Studio(args.projects_dir, args.python)

    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError as exc:
        parser.exit(1, f"无法启动本地服务：{exc}\n")

    server.studio = studio

    if args.project is not None:
        try:
            project = studio.open_or_create(args.project)
            studio.initial_project = project["name"]
            print(f"Project: {project['path']}", flush=True)
        except (EditorError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
            server.server_close()
            studio.close()
            parser.exit(1, f"无法打开或创建项目：{exc}\n")

    url = f"http://127.0.0.1:{server.server_address[1]}"
    print(f"OneSite Studio: {url}\nProjects: {studio.root}\nPython: {studio.python}", flush=True)

    if not studio.catalog["available"]:
        print(
            "OneSite 不可用。请使用已安装 OneSite 的 Python 或 --python 指定环境。\n"
            + studio.catalog["error"],
            flush=True,
        )

    if not args.no_browser:
        webbrowser.open(url)

    def shutdown(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, shutdown)

    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        studio.close()


if __name__ == "__main__":
    main()
