"""WebUI HTTP请求处理器."""

from __future__ import annotations

import json
import secrets
import subprocess
import sys
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlsplit

from .assets import ASSETS
from .constants import MAX_BODY, MAX_FILE, MODEL_IMPORTS
from .exceptions import EditorError
from .file_utils import is_editable
from .parsers import parse_config, parse_model, render_config, render_model
from .studio import Studio
from .utils import check_python


class Handler(BaseHTTPRequestHandler):
    """HTTP请求处理器.

    处理GET请求（静态资源和HTML页面）和POST请求（JSON API）。
    """

    server_version = "OneSiteStudio/1"

    def log_message(self, fmt: str, *args: Any) -> None:
        """静默日志（安全考虑，不记录项目内容、token或查询参数）."""
        pass

    @property
    def studio(self) -> Studio:
        """访问server的Studio实例."""
        return self.server.studio

    def send(
        self,
        status: int,
        body: Any,
        html: bool = False,
        asset_type: str | None = None,
    ) -> None:
        """统一响应：JSON/HTML/gzip资产，含完整安全头.

        Args:
            status: HTTP状态码
            body: 响应体
            html: 是否为HTML响应
            asset_type: 资产MIME类型（用于gzip压缩的静态资源）
        """
        payload = (
            body
            if asset_type
            else (body.encode() if html else json.dumps(body, ensure_ascii=False).encode())
        )
        self.send_response(status)
        self.send_header(
            "Content-Type",
            asset_type
            or ("text/html; charset=utf-8" if html else "application/json; charset=utf-8"),
        )
        if asset_type:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'nonce-"
            + self.studio.token
            + "'; style-src 'self' 'unsafe-inline'; connect-src 'self'; "
            "img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        )
        self.end_headers()
        self.wfile.write(payload)

    def guard(self, api: bool = False) -> None:
        """安全防护：Host/Origin/Cross-site校验，API Token验证.

        Args:
            api: 是否为API请求（需要验证token）

        Raises:
            EditorError: 安全校验失败时抛出
        """
        port = self.server.server_address[1]
        allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if self.headers.get("Host") not in allowed:
            raise EditorError("Invalid host", 403)
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://{host}" for host in allowed}:
            raise EditorError("Cross-origin requests are not allowed", 403)
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            raise EditorError("Cross-site requests are not allowed", 403)
        if api and not secrets.compare_digest(
            self.headers.get("X-Studio-Token", ""), self.studio.token
        ):
            raise EditorError("Invalid studio token; reload the page", 403)

    def do_GET(self) -> None:
        """处理GET请求：静态资源分发 + HTML入口页."""
        try:
            self.guard()
            path = urlsplit(self.path).path
            if path in ASSETS:
                mime, payload = ASSETS[path]
                self.send(200, payload, asset_type=mime)
                return
            if path not in {"/", "/favicon.ico"}:
                raise EditorError("Not found", 404)
            if path == "/favicon.ico":
                self.send(200, {})
            else:
                self.send(200, HTML.replace("__STUDIO_TOKEN__", self.studio.token), html=True)
        except EditorError as exc:
            self.send(exc.status, {"error": str(exc)})

    def do_POST(self) -> None:
        """处理POST请求：JSON请求解析 + 错误处理."""
        try:
            self.guard(api=True)
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                raise EditorError("Expected application/json", 415)
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                raise EditorError("请求大小超过限制", 413)
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise EditorError("Expected an object")
            self.send(200, self.dispatch(urlsplit(self.path).path, data))
        except EditorError as exc:
            self.send(exc.status, {"error": str(exc)})
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            self.send(400, {"error": f"请求无效：{exc}"})
        except subprocess.TimeoutExpired:
            self.send(504, {"error": "命令执行超时，请检查 OneSite 环境。"})
        except OSError as exc:
            self.send(500, {"error": f"文件或进程操作失败：{exc}"})

    def dispatch(self, path: str, data: dict[str, Any]) -> Any:
        """API路由分发.

        Args:
            path: 请求路径
            data: 请求数据

        Returns:
            响应数据

        Raises:
            EditorError: 路由不存在或处理失败时抛出
        """
        studio = self.studio
        if path == "/api/bootstrap":
            return {
                "projects": studio.listing(),
                "native_picker": sys.platform == "darwin",
                "initial_project": studio.initial_project,
                "root": str(studio.root),
                "catalog": studio.catalog,
                "python": studio.python,
                "model_imports": MODEL_IMPORTS,
            }
        if path == "/api/select-directory":
            return studio.select_directory()
        if path == "/api/directories":
            return studio.browse_directories(data.get("path"))
        if path == "/api/create":
            return studio.create(data["name"])
        if path == "/api/open":
            with studio.lock:
                if "path" in data:
                    return studio.open_path(data["path"])
                return studio.read(data["name"])
        if path == "/api/save":
            return studio.save(data["name"], data["files"], data["revision"], data.get("baseline"))
        if path == "/api/parse":
            return (parse_config if data["kind"] == "config" else parse_model)(data["source"])
        if path == "/api/render":
            return {
                "source": (render_config if data["kind"] == "config" else render_model)(
                    data["spec"]
                )
            }
        if path == "/api/validate":
            for name, source in data["files"].items():
                if not is_editable(name):
                    raise EditorError(f"不可编辑的路径：{name}")
                if not isinstance(source, str) or len(source.encode()) > MAX_FILE:
                    raise EditorError(f"文件过大或内容无效：{name}")
                if name.endswith(".py"):
                    check_python(source, name)
                if name.endswith(".json"):
                    json.loads(source)
            return {"valid": True}
        if path == "/api/start":
            return studio.start(
                data["name"], data["action"], data.get("options", {}), data["revision"]
            )
        if path == "/api/jobs":
            with studio.lock:
                return {
                    "jobs": [
                        j.snapshot(int(data.get("cursors", {}).get(j.id, 0)))
                        for j in studio.jobs.values()
                        if j.project == data["name"]
                    ]
                }
        if path == "/api/stop":
            job = studio.jobs.get(data["id"])
            if job is None:
                raise EditorError("命令不存在", 404)
            job.stop()
            return job.snapshot()
        raise EditorError("Not found", 404)


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <meta name="studio-token" content="__STUDIO_TOKEN__" />
  <title>OneSite Studio</title>
  <link rel="stylesheet" href="/assets/studio.css" />
</head>
<body>
  <div id="root"></div>
  <script nonce="__STUDIO_TOKEN__" src="/assets/studio.js"></script>
</body>
</html>
"""
