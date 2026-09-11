"""WebUI 自定义异常."""

from __future__ import annotations


class EditorError(Exception):
    """编辑器错误，携带HTTP状态码."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status
