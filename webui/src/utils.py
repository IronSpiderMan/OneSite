"""WebUI 通用工具函数."""

from __future__ import annotations

import ast
import keyword
import pprint
from typing import Any

from .exceptions import EditorError


def python_literal(value: Any) -> str:
    """将Python值转换为格式化的字符串表示."""
    return pprint.pformat(value, width=100, sort_dicts=False)


def check_python(source: str, filename: str) -> ast.AST:
    """验证Python源码语法正确性.

    Args:
        source: Python源码字符串
        filename: 文件名（用于错误消息）

    Returns:
        解析后的AST树

    Raises:
        EditorError: 语法错误时抛出
    """
    try:
        tree = ast.parse(source, filename=filename)
        compile(tree, filename, "exec")
        return tree
    except (SyntaxError, ValueError) as exc:
        raise EditorError(f"{filename}: {exc}") from exc


def identifier(value: str) -> str:
    """验证有效的Python标识符.

    Args:
        value: 待验证的字符串

    Returns:
        验证通过的标识符

    Raises:
        EditorError: 无效标识符时抛出
    """
    if not isinstance(value, str) or not value.isidentifier() or keyword.iskeyword(value):
        raise EditorError(f"无效的 Python 标识符：{value!r}")
    return value


def expression(value: str) -> str:
    """验证有效的Python表达式.

    Args:
        value: 待验证的字符串

    Returns:
        验证通过的表达式

    Raises:
        EditorError: 无效表达式时抛出
    """
    if not isinstance(value, str) or not value.strip():
        raise EditorError("Python 表达式不能为空")
    try:
        ast.parse(value, mode="eval")
    except SyntaxError as exc:
        raise EditorError(f"无效的 Python 表达式：{value}: {exc.msg}") from exc
    return value
