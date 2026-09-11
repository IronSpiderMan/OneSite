"""WebUI Studio 核心业务逻辑.

管理项目目录、文件读写、CLI子进程调度、冲突检测与合并。
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from .constants import HOOKS, MAX_FILE, SKIP_DIRS
from .exceptions import EditorError
from .file_utils import digest, is_editable, safe_file
from .job import Job
from .utils import check_python


class Studio:
    """核心业务层：项目管理、文件操作、CLI调度."""

    def __init__(self, root: Path, python: str = sys.executable):
        """初始化Studio.

        Args:
            root: 项目根目录
            python: Python解释器路径
        """
        self.root = root.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        # Resolving a venv Python symlink would silently switch to its base
        # interpreter and lose the user's installed OneSite/dependencies.
        self.python = os.path.abspath(os.path.expanduser(python))
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.jobs: dict[str, Job] = {}
        self.opened_projects: dict[str, Path] = {}
        self.picker_lock = threading.Lock()
        self.initial_project: str | None = None
        self.env = dict(os.environ, PYTHONUNBUFFERED="1", NO_COLOR="1", TERM="dumb")
        self.env["PATH"] = str(Path(self.python).parent) + os.pathsep + self.env.get("PATH", "")
        self.cli = [self.python, "-m", "onesite.main"]
        self.catalog = self._catalog()

    def _catalog(self) -> dict[str, Any]:
        """子进程获取OneSite schema.

        Returns:
            包含SiteConfig和OneSiteConfig的schema字典
        """
        script = (
            "import json; from onesite.config import SiteConfig, OneSiteConfig; "
            "print(json.dumps({'site': SiteConfig.model_json_schema(), "
            "'model': OneSiteConfig.model_json_schema()}))"
        )
        try:
            result = subprocess.run(
                [self.python, "-c", script],
                env=self.env,
                cwd=Path(__file__).resolve().parent,
                capture_output=True,
                text=True,
                timeout=20,
            )
            if result.returncode:
                raise RuntimeError(result.stderr.strip())
            return {**json.loads(result.stdout), "available": True, "hooks": HOOKS}
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
            return {
                "available": False,
                "error": str(exc),
                "hooks": HOOKS,
                "site": {"properties": {}},
                "model": {"properties": {}},
            }

    def select_directory(self) -> dict[str, Any]:
        """macOS原生文件夹选择器.

        Returns:
            包含选择路径的字典

        Raises:
            EditorError: 非macOS系统或选择失败时抛出
        """
        if sys.platform != "darwin":
            raise EditorError("当前系统请使用网页目录选择器")
        if not self.picker_lock.acquire(blocking=False):
            raise EditorError("文件夹选择窗口已打开，请先完成选择", 409)
        # Pass paths as argv, never interpolate them into AppleScript source.
        script = """on run argv
    try
        tell application "System Events"
            activate
            set selectedFolder to choose folder with prompt "选择 OneSite 项目目录" default location (POSIX file (item 1 of argv))
        end tell
        return POSIX path of selectedFolder
    on error number -128
        return ""
    end try
end run"""
        try:
            result = subprocess.run(
                ["/usr/bin/osascript", "-e", script, str(self.root)],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode:
                raise EditorError("无法打开系统文件夹选择器，请使用网页目录选择。")
            return {"path": result.stdout.rstrip("\r\n") or None}
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise EditorError("系统文件夹选择器不可用或等待超时，请重新选择。") from exc
        finally:
            self.picker_lock.release()

    def browse_directories(self, value: str | None = None) -> dict[str, Any]:
        """Web端目录浏览.

        Args:
            value: 目录路径（可选）

        Returns:
            包含目录信息的字典

        Raises:
            EditorError: 路径无效或权限不足时抛出
        """
        if value is not None and (not isinstance(value, str) or not value):
            raise EditorError("目录路径无效")
        try:
            path = Path(value).expanduser() if value else self.root
            if not path.is_absolute():
                path = self.root / path
            path = path.resolve(strict=True)
            if not path.is_dir():
                raise EditorError("请选择目录")
            directories = []
            for child in path.iterdir():
                try:
                    if child.is_dir():
                        directories.append({"name": child.name, "path": str(child)})
                except OSError:
                    continue
            is_project = any(
                (path / name).is_file() and not (path / name).is_symlink()
                for name in ("site_config.py", "site_config.json")
            )
        except PermissionError as exc:
            raise EditorError("没有权限读取该目录", 403) from exc
        except (OSError, ValueError, RuntimeError) as exc:
            raise EditorError("目录不存在或无法读取", 404) from exc
        return {
            "path": str(path),
            "parent": str(path.parent) if path.parent != path else None,
            "home": str(Path.home()),
            "root": str(self.root),
            "is_project": is_project,
            "directories": sorted(directories, key=lambda item: item["name"].casefold()),
        }

    def open_path(self, value: str) -> dict[str, Any]:
        """通过绝对路径打开已有项目.

        Args:
            value: 项目目录路径

        Returns:
            项目信息字典

        Raises:
            EditorError: 路径无效或非OneSite项目时抛出
        """
        if not isinstance(value, str) or not value.strip():
            raise EditorError("请输入项目目录路径")
        try:
            path = Path(value.strip()).expanduser()
            if not path.is_absolute():
                path = self.root / path
            path = path.resolve(strict=True)
        except (OSError, ValueError, RuntimeError) as exc:
            raise EditorError("项目目录不存在或路径无效", 404) from exc
        if not path.is_dir():
            raise EditorError("请选择项目目录，而不是文件")
        if not any(
            (path / config).is_file() and not (path / config).is_symlink()
            for config in ("site_config.py", "site_config.json")
        ):
            raise EditorError("该目录不是 OneSite 项目：缺少 site_config.py 或 site_config.json")
        with self.lock:
            # Use the canonical path as identity outside the default workspace;
            # projects with the same basename must not share drafts or jobs.
            name = str(path)
            if path.parent == self.root and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", path.name):
                name = path.name
            self.opened_projects[name] = path
            try:
                return self.read(name)
            except Exception:
                self.opened_projects.pop(name, None)
                raise

    def project(self, name: str, must_exist: bool = True) -> Path:
        """校验并解析项目名到路径.

        Args:
            name: 项目名称
            must_exist: 是否要求项目已存在

        Returns:
            项目路径

        Raises:
            EditorError: 项目名无效或不存在时抛出
        """
        if must_exist and isinstance(name, str) and name in self.opened_projects:
            path = self.opened_projects[name]
            if path.is_symlink() or path.resolve() != path:
                raise EditorError("项目路径已发生变化，请重新打开项目")
            if not path.is_dir():
                raise EditorError("项目不存在", 404)
            return path
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", name):
            raise EditorError("项目名需以英文字母开头，只含字母、数字、_ 或 -，最长 64 字符。")
        path = self.root / name
        if path.is_symlink() or path.resolve().parent != self.root:
            raise EditorError("项目不可为符号链接")
        if must_exist and not path.is_dir():
            raise EditorError("项目不存在", 404)
        return path

    def listing(self) -> list[dict[str, str]]:
        """列出所有已知项目.

        Returns:
            项目列表，每个包含name和path
        """
        result = []
        for path in sorted(self.root.iterdir()):
            if (
                path.is_dir()
                and not path.is_symlink()
                and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", path.name)
            ):
                if any((path / name).is_file() for name in ("site_config.py", "site_config.json")):
                    result.append({"name": path.name, "path": str(path)})
        known = {item["name"] for item in result}
        result.extend(
            {"name": name, "path": str(path)}
            for name, path in self.opened_projects.items()
            if name not in known and path.is_dir()
        )
        return result

    def read(self, name: str) -> dict[str, Any]:
        """读取项目所有可编辑文件内容.

        Args:
            name: 项目名称

        Returns:
            包含文件内容和revision的字典
        """
        project = self.project(name)
        files, skipped = {}, []
        for base, dirs, names in os.walk(project, followlinks=False):
            # Source only: never scan generated output or node_modules.
            dirs[:] = [
                d
                for d in dirs
                if d not in SKIP_DIRS
                and not (Path(base) / d).is_symlink()
                and (Path(base) != project or d in {"app", "deploy"})
            ]
            for item in sorted(names):
                path = Path(base) / item
                rel = path.relative_to(project).as_posix()
                if not is_editable(rel):
                    continue
                if path.is_symlink() or path.stat().st_size > MAX_FILE:
                    skipped.append(rel)
                    continue
                try:
                    files[rel] = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    skipped.append(rel)
        return {
            "name": name,
            "path": str(project),
            "files": files,
            "revision": digest(files),
            "skipped": skipped,
        }

    def active(self, name: str) -> list[Job]:
        """获取指定项目正在运行的Job列表.

        Args:
            name: 项目名称

        Returns:
            活跃的Job列表
        """
        return [j for j in self.jobs.values() if j.project == name and j.finished is None]

    def open_or_create(self, value: str) -> dict[str, Any]:
        """路径存在则打开，否则创建.

        Args:
            value: 项目路径或名称

        Returns:
            项目信息字典
        """
        target = Path(value).expanduser().absolute()
        if target.exists() or target.is_symlink():
            return self.open_path(str(target))
        return self._create_target(target)

    def create(self, name: str) -> dict[str, Any]:
        """通过项目名创建新项目.

        Args:
            name: 项目名称

        Returns:
            项目信息字典
        """
        return self._create_target(self.project(name, False))

    def _create_target(self, target: Path) -> dict[str, Any]:
        """实际创建逻辑（原子性临时目录 + CLI create）.

        Args:
            target: 项目目标路径

        Returns:
            项目信息字典

        Raises:
            EditorError: 创建失败时抛出
        """
        name = target.name
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", name):
            raise EditorError("新项目名需以英文字母开头，只含字母、数字、_ 或 -，最长 64 字符。")
        with self.lock:
            if target.exists():
                raise EditorError("项目已存在，请打开现有项目。", 409)
            # A failed CLI create must not leave a half-created project visible.
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".webui-create-", dir=target.parent) as tmp:
                result = subprocess.run(
                    self.cli + ["create", name],
                    cwd=tmp,
                    env=self.env,
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
                if result.returncode or not (Path(tmp) / name / "site_config.py").exists():
                    raise EditorError("site create 失败：\n" + result.stdout + result.stderr)
                os.rename(Path(tmp) / name, target)
            return self.open_path(str(target))

    def save(
        self,
        name: str,
        files: dict[str, str],
        revision: str,
        baseline: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """保存文件，含冲突检测、合并、验证、回滚.

        Args:
            name: 项目名称
            files: 文件路径到内容的映射
            revision: 当前revision
            baseline: 基线文件内容（用于冲突合并）

        Returns:
            更新后的项目信息

        Raises:
            EditorError: 保存失败时抛出
        """
        with self.lock:
            if self.active(name):
                raise EditorError("请先停止当前项目的命令，再保存或修改源文件。", 409)
            current = self.read(name)
            if revision != current["revision"]:
                if not isinstance(baseline, dict) or digest(baseline) != revision:
                    raise EditorError(
                        "磁盘内容已被其他窗口或编辑器修改。请先导出草稿，再重新打开项目合并修改。",
                        409,
                    )
                if not isinstance(files, dict):
                    raise EditorError("文件集合无效")
                # site sync itself can scaffold app files. Merge independent
                # edits against the editor's baseline, never overwrite an
                # externally edited file when both sides changed it.
                missing = object()
                local_changes = {
                    key
                    for key in set(baseline) | set(files)
                    if baseline.get(key, missing) != files.get(key, missing)
                }
                conflicts = [
                    key
                    for key in local_changes
                    if current["files"].get(key, missing) != baseline.get(key, missing)
                    and current["files"].get(key, missing) != files.get(key, missing)
                ]
                if conflicts:
                    raise EditorError(
                        "以下文件同时在网页和磁盘中被修改，请导出草稿后合并：\n"
                        + "\n".join(sorted(conflicts)),
                        409,
                    )
                merged = dict(current["files"])
                for key in local_changes:
                    if key in files:
                        merged[key] = files[key]
                    else:
                        merged.pop(key, None)
                files = merged
            if not isinstance(files, dict) or len(files) > 1500:
                raise EditorError("文件集合无效或超过 1500 个文件")
            if not any(k in files for k in ("site_config.py", "site_config.json")):
                raise EditorError("项目必须保留 site_config.py 或 site_config.json")
            project = self.project(name)
            for rel, content in files.items():
                target = safe_file(project, rel)
                if target.exists() and rel not in current["files"]:
                    raise EditorError(f"{rel} 未被编辑器加载，不能覆盖。")
                if not isinstance(content, str) or len(content.encode()) > MAX_FILE:
                    raise EditorError(f"文件过大或内容无效：{rel}")
                if rel.endswith(".py"):
                    check_python(content, rel)
                elif rel.endswith(".json"):
                    try:
                        json.loads(content)
                    except ValueError as exc:
                        raise EditorError(f"{rel}: {exc}") from exc
            changed = {k: v for k, v in files.items() if current["files"].get(k) != v}
            deleted = set(current["files"]) - set(files)
            # Stage and validate the entire change set before touching files. Keep
            # the original bytes for rollback if any filesystem operation fails.
            with tempfile.TemporaryDirectory(prefix=".webui-save-", dir=project) as tmp:
                stage = Path(tmp)
                for rel, content in changed.items():
                    path = stage / rel
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8")
                    old = safe_file(project, rel)
                    if old.exists():
                        shutil.copymode(old, path)
                touched = []
                try:
                    for rel in changed:
                        target = safe_file(project, rel)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        os.replace(stage / rel, target)
                        touched.append(rel)
                    for rel in deleted:
                        safe_file(project, rel).unlink()
                        touched.append(rel)
                except OSError:
                    for rel in reversed(touched):
                        target = safe_file(project, rel)
                        if rel in current["files"]:
                            target.write_text(current["files"][rel], encoding="utf-8")
                        else:
                            target.unlink(missing_ok=True)
                    raise
            return self.read(name)

    def start(self, name: str, action: str, options: dict[str, Any], revision: str) -> dict[str, Any]:
        """启动CLI命令.

        Args:
            name: 项目名称
            action: 操作类型（sync/run）
            options: 命令选项
            revision: 当前revision

        Returns:
            Job快照

        Raises:
            EditorError: 启动失败时抛出
        """
        with self.lock:
            project = self.project(name)
            if self.active(name):
                raise EditorError("该项目已有命令正在执行，请先停止或等待完成。", 409)
            if self.read(name)["revision"] != revision:
                raise EditorError("项目内容已变化，请重新打开后再执行。", 409)
            if action == "sync":
                argv = self.cli + ["sync"]
                if options.get("install"):
                    argv.append("--install")
                if options.get("build_cmd"):
                    argv.append("--build-cmd")
            elif action == "run":
                component = options.get("component", "all")
                if component not in {"all", "frontend", "backend"}:
                    raise EditorError("无效的运行组件")
                required = []
                if component in {"all", "backend"}:
                    required.append(project / "generated/backend/app/api/api.py")
                if component in {"all", "frontend"}:
                    required.append(project / "generated/frontend/src/Routes.tsx")
                if any(not path.exists() for path in required):
                    raise EditorError("请先执行 Sync 生成项目代码。")
                # The current CLI uses --component, not a positional component.
                argv = self.cli + ["run", ".", "--component", component, "--host", "127.0.0.1"]
            else:
                raise EditorError("仅支持 sync 和 run")
            # Bound retained job history without discarding active commands.
            for job_id in list(self.jobs):
                if len(self.jobs) < 60:
                    break
                if self.jobs[job_id].finished is not None:
                    del self.jobs[job_id]
            job = Job(name, action, argv, project, self.env)
            self.jobs[job.id] = job
            return job.snapshot()

    def close(self) -> None:
        """停止所有运行中的Job."""
        for job in list(self.jobs.values()):
            job.stop()
