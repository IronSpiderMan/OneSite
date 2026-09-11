"""WebUI 常量定义."""

from __future__ import annotations

# 文件大小限制
MAX_BODY = 16 * 1024 * 1024
MAX_FILE = 2 * 1024 * 1024

# 可编辑的文本文件扩展名
TEXT_EXTENSIONS = {
    ".py",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".txt",
    ".md",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".css",
    ".html",
    ".svg",
    ".sql",
    ".sh",
    ".rs",
    ".go",
    ".mod",
    ".sum",
    ".lock",
    ".ini",
    ".mako",
}

# 跳过的目录
SKIP_DIRS = {"__pycache__", "node_modules", ".git", ".venv", "target", "dist"}

# 模型导入模板
MODEL_IMPORTS = """from typing import Any, Optional, List, Dict
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4
from sqlalchemy import Column, JSON, DateTime
from sqlmodel import Field, Relationship, SQLModel
"""

# Hook定义
HOOKS = {
    "on_before_create": ("self, session, context", "创建前；可修改 self，抛出异常会回滚事务。"),
    "on_after_create": ("self, session, context", "创建后、事务提交前；可使用同一 session。"),
    "on_before_update": (
        "self, session, old, changes, context",
        "更新前；old 为旧值，changes 为更新内容。",
    ),
    "on_after_update": ("self, session, old, changes, context", "更新后、事务提交前。"),
    "on_before_delete": ("self, session, old, context", "删除前、事务内。"),
    "on_after_delete": ("self, session, old, context", "删除后、事务提交前。"),
    "on_after_commit_create": (
        "self, context",
        "创建提交后；适合通知等外部副作用，不提供 session。",
    ),
    "on_after_commit_update": ("self, old, changes, context", "更新提交后；适合通知等外部副作用。"),
    "on_after_commit_delete": ("self, old, context", "删除提交后。"),
    "on_after_bulk_delete": (
        "cls, session, olds, context",
        "批量删除后、事务内；必须是 classmethod。",
    ),
    "on_after_commit_bulk_delete": ("cls, olds, context", "批量删除提交后；必须是 classmethod。"),
}
