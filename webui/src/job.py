"""WebUI 子进程作业管理."""

from __future__ import annotations

import os
import secrets
import signal
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any


class Job:
    """管理单个子进程作业（CLI命令执行）.

    支持线程安全的增量日志读取和跨平台进程终止。
    """

    def __init__(
        self,
        project: str,
        action: str,
        argv: list[str],
        cwd: Path,
        env: dict[str, str],
    ):
        """初始化并启动子进程.

        Args:
            project: 项目名称
            action: 操作类型（sync/run等）
            argv: 命令行参数
            cwd: 工作目录
            env: 环境变量
        """
        self.id = secrets.token_hex(8)
        self.project = project
        self.action = action
        self.argv = argv
        self.lines: deque[dict[str, Any]] = deque(maxlen=3000)
        self.sequence = 0
        self.lock = threading.Lock()
        self.started = time.time()
        self.finished: float | None = None
        self.code: int | None = None
        self.stopping = False
        self.process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        """后台线程：增量读取stdout并存入deque."""
        import codecs

        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        try:
            while chunk := self.process.stdout.read1(4096):
                value = decoder.decode(chunk)
                with self.lock:
                    self.sequence += 1
                    self.lines.append({"seq": self.sequence, "text": value})
        finally:
            self.process.stdout.close()
            self.code = self.process.wait()
            self.finished = time.time()

    def snapshot(self, after: int = 0) -> dict[str, Any]:
        """返回作业状态快照（含增量日志）.

        Args:
            after: 只返回此序号之后的日志行

        Returns:
            包含作业状态和日志的字典
        """
        with self.lock:
            return {
                "id": self.id,
                "project": self.project,
                "action": self.action,
                "argv": self.argv,
                "started": self.started,
                "finished": self.finished,
                "code": self.code,
                "running": self.finished is None,
                "stopping": self.stopping,
                "cursor": self.sequence,
                "truncated": bool(self.lines and after < self.lines[0]["seq"] - 1),
                "logs": [line for line in self.lines if line["seq"] > after],
            }

    def stop(self) -> None:
        """终止进程（SIGTERM后SIGKILL，跨平台）."""
        if self.finished is not None:
            return
        self.stopping = True
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                    capture_output=True,
                    timeout=10,
                )
            else:
                # Always signal the process group, including when its leader has
                # exited but a reload worker still holds the stdout pipe open.
                os.killpg(self.process.pid, signal.SIGTERM)
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    try:
                        os.killpg(self.process.pid, 0)
                    except ProcessLookupError:
                        return
                    time.sleep(0.05)
                os.killpg(self.process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
