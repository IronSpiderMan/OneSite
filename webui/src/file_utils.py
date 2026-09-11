"""WebUI 文件操作工具."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

from .constants import SKIP_DIRS, TEXT_EXTENSIONS
from .exceptions import EditorError


def is_editable(relative: str) -> bool:
    """判断文件路径是否可编辑.

    Args:
        relative: 相对路径字符串

    Returns:
        如果文件可编辑返回True
    """
    p = PurePosixPath(relative)
    if (
        not relative
        or "\\" in relative
        or p.is_absolute()
        or ".." in p.parts
        or str(p) != relative
        or any(part in SKIP_DIRS for part in p.parts)
    ):
        return False
    if relative in {
        "site_config.py",
        "site_config.json",
        "visualizations.py",
        "deploy/.env",
        "deploy/.env.example",
    }:
        return True
    return (
        len(p.parts) > 1
        and p.parts[0] == "app"
        and (p.suffix in TEXT_EXTENSIONS or p.name in {"Dockerfile", "Makefile", "Cargo.lock"})
    )


def safe_file(project: Path, relative: str) -> Path:
    """安全地构建文件路径（防目录遍历攻击）.

    Args:
        project: 项目根目录
        relative: 相对路径

    Returns:
        安全的绝对路径

    Raises:
        EditorError: 路径不安全时抛出
    """
    if not isinstance(relative, str) or not is_editable(relative):
        raise EditorError(f"不可编辑的路径：{relative!r}")
    target = project / relative
    for p in (target, *target.parents):
        if p == project:
            break
        if p.is_symlink():
            raise EditorError(f"不允许通过符号链接编辑：{relative}")
    if not target.resolve().is_relative_to(project.resolve()):
        raise EditorError("路径超出项目目录")
    return target


def digest(files: dict[str, str]) -> str:
    """计算文件集合的SHA-256哈希（用于冲突检测和revision）.

    Args:
        files: 文件路径到内容的映射

    Returns:
        十六进制哈希字符串
    """
    return hashlib.sha256(
        json.dumps(files, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
