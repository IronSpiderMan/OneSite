"""WebUI 配置和模型解析器.

提供Python AST解析功能，用于site_config.py和model.py的双向转换：
- parse_config / render_config: site_config.py <-> JSON spec
- parse_model / render_model: model.py <-> JSON spec
"""

from __future__ import annotations

import ast
import copy
import textwrap
from typing import Any

from .constants import MODEL_IMPORTS
from .exceptions import EditorError
from .utils import check_python, expression, identifier, python_literal


def static_value(node: ast.expr) -> Any:
    """递归读取AST字面量节点（支持Config构造器）.

    Args:
        node: AST节点

    Returns:
        Python值

    Raises:
        ValueError: 节点包含动态表达式时抛出
    """
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id == "sqlite_url" and not node.keywords and len(node.args) <= 1:
            path = ast.literal_eval(node.args[0]) if node.args else "app.db"
            return f"sqlite:///./{path.lstrip('./')}"
        if node.func.id.endswith("Config") or node.func.id in {"SiteConfig", "OneSiteConfig"}:
            if node.args or any(k.arg is None for k in node.keywords):
                raise ValueError("展开参数需使用源码编辑")
            return {k.arg: static_value(k.value) for k in node.keywords}
    if isinstance(node, ast.Dict):
        return {ast.literal_eval(k): static_value(v) for k, v in zip(node.keys, node.values)}
    if isinstance(node, (ast.List, ast.Tuple)):
        return [static_value(v) for v in node.elts]
    return ast.literal_eval(node)


def parse_config(source: str) -> dict[str, Any]:
    """将site_config.py源码解析为结构化spec.

    Args:
        source: Python源码

    Returns:
        结构化配置spec，包含values, expressions, prefix, suffix

    Raises:
        EditorError: 解析失败时抛出
    """
    tree = check_python(source, "site_config.py")
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            if isinstance(node.targets[0], ast.Name) and node.targets[0].id == "config":
                # Preserve expressions such as env(...) per top-level key.
                if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                    if node.value.func.id != "SiteConfig" or node.value.args:
                        break
                    values, expressions = {}, {}
                    for kw in node.value.keywords:
                        if kw.arg is None:
                            raise EditorError("config 含 ** 展开，请使用源码编辑。")
                        try:
                            values[kw.arg] = static_value(kw.value)
                        except (ValueError, TypeError):
                            expressions[kw.arg] = ast.get_source_segment(source, kw.value)
                    return {
                        "values": values,
                        "expressions": expressions,
                        "prefix": "\n".join(source.splitlines()[: node.lineno - 1]),
                        "suffix": "\n".join(source.splitlines()[node.end_lineno :]),
                    }
    raise EditorError("配置采用动态 Python 写法，请使用源码编辑；文件会完整保留。")


def render_config(spec: dict[str, Any]) -> str:
    """将结构化spec渲染回site_config.py源码.

    Args:
        spec: 结构化配置spec

    Returns:
        Python源码

    Raises:
        EditorError: 渲染失败时抛出
    """
    values = spec.get("values", {})
    expressions = spec.get("expressions", {})
    if not isinstance(values, dict) or not isinstance(expressions, dict):
        raise EditorError("配置值和表达式必须是对象")
    pairs = [
        f"    {identifier(k)}={python_literal(v)},"
        for k, v in values.items()
        if k not in expressions
    ]
    pairs += [f"    {identifier(k)}={expression(v)}," for k, v in expressions.items()]
    source = (
        spec.get("prefix", "from onesite.config import SiteConfig, env, sqlite_url")
        + "\n\nconfig = SiteConfig(\n"
        + "\n".join(pairs)
        + "\n)\n"
        + spec.get("suffix", "")
    )
    check_python(source, "site_config.py")
    return source


def parse_model(source: str) -> dict[str, Any]:
    """将model.py源码解析为结构化spec.

    Args:
        source: Python源码

    Returns:
        结构化模型spec，包含name, table, config, fields, hooks等

    Raises:
        EditorError: 解析失败时抛出
    """
    tree = check_python(source, "model.py")
    # Keep inheritance, helper enums, decorators and unusual class definitions in
    # the source editor rather than attempting a lossy round trip.
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    if len(classes) != 1:
        raise EditorError("此文件包含多个类或继承结构，请使用源码编辑，原有内容不会被转换。")
    cls = classes[0]
    if (
        cls.decorator_list
        or len(cls.bases) != 1
        or not isinstance(cls.bases[0], ast.Name)
        or cls.bases[0].id != "SQLModel"
        or any(k.arg != "table" for k in cls.keywords)
    ):
        raise EditorError("此模型使用自定义继承或装饰器，请使用源码编辑。")
    result = {
        "name": cls.name,
        "table": any(ast.literal_eval(k.value) for k in cls.keywords),
        "table_name": "",
        "config": {},
        "fields": [],
        "hooks": "",
        "extra": "",
        "docstring": "",
        "prefix": "\n".join(source.splitlines()[: cls.lineno - 1]),
        "suffix": "\n".join(source.splitlines()[cls.end_lineno :]),
    }
    extra, methods = [], []
    for node in cls.body:
        if (
            node is cls.body[0]
            and isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
        ):
            if isinstance(node.value.value, str):
                result["docstring"] = repr(node.value.value)
                continue
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            name = node.targets[0].id
            if name == "__onesite__":
                try:
                    result["config"] = static_value(node.value)
                    if not isinstance(result["config"], dict):
                        raise ValueError("__onesite__ 必须是字典")
                except (ValueError, TypeError) as exc:
                    raise EditorError("__onesite__ 包含动态表达式，请使用源码编辑。") from exc
                continue
            if name == "__tablename__":
                result["table_name"] = ast.literal_eval(node.value)
                continue
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id.startswith("__") or methods:
                raise EditorError("此类的字段声明依赖特殊定义顺序，请使用源码编辑。")
            field = {
                "name": node.target.id,
                "type": ast.get_source_segment(source, node.annotation),
                "kwargs": {},
                "props": {},
                "value": None,
            }
            call = node.value
            if (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id == "Field"
            ):
                if call.args or any(k.arg is None for k in call.keywords):
                    raise EditorError("Field 含位置参数或展开参数，请使用源码编辑。")
                for kw in call.keywords:
                    field["kwargs"][kw.arg] = ast.get_source_segment(source, kw.value)
                if "sa_column_kwargs" in field["kwargs"]:
                    try:
                        column = ast.literal_eval(field["kwargs"]["sa_column_kwargs"])
                        info = column.get("info", {})
                        if isinstance(info.get("site_props"), dict):
                            field["props"] = info.pop("site_props")
                            if not info:
                                column.pop("info", None)
                            if column:
                                field["kwargs"]["sa_column_kwargs"] = python_literal(column)
                            else:
                                del field["kwargs"]["sa_column_kwargs"]
                    except (ValueError, TypeError, AttributeError):
                        pass
                elif "sa_column" in field["kwargs"]:
                    try:
                        column = ast.parse(field["kwargs"]["sa_column"], mode="eval").body
                        if (
                            isinstance(column, ast.Call)
                            and (
                                (isinstance(column.func, ast.Name) and column.func.id == "Column")
                                or (
                                    isinstance(column.func, ast.Attribute)
                                    and column.func.attr == "Column"
                                )
                            )
                            and not any(k.arg is None for k in column.keywords)
                        ):
                            info_kw = next((k for k in column.keywords if k.arg == "info"), None)
                            info = ast.literal_eval(info_kw.value) if info_kw else {}
                            if isinstance(info.get("site_props"), dict):
                                field["props"] = info.pop("site_props")
                                if info:
                                    info_kw.value = ast.parse(
                                        python_literal(info), mode="eval"
                                    ).body
                                else:
                                    column.keywords.remove(info_kw)
                                field["kwargs"]["sa_column"] = ast.unparse(column)
                    except (ValueError, TypeError, AttributeError, SyntaxError):
                        pass
            elif call is not None:
                field["value"] = ast.get_source_segment(source, call)
            else:
                field["value"] = ""
            result["fields"].append(field)
            continue
        start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
        block = textwrap.dedent("\n".join(source.splitlines()[start - 1 : node.end_lineno]))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(block)
        elif not isinstance(node, ast.Pass):
            if not (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id in {"__table_args__", "__mapper_args__"}
            ):
                raise EditorError("此类包含自定义类语句，请使用源码编辑以保留执行顺序。")
            extra.append(block)
    result["hooks"] = "\n\n".join(methods)
    result["extra"] = "\n\n".join(extra)
    return result


def render_model(spec: dict[str, Any]) -> str:
    """将结构化spec渲染回model.py源码.

    Args:
        spec: 结构化模型spec

    Returns:
        Python源码

    Raises:
        EditorError: 渲染失败时抛出
    """
    name = identifier(spec.get("name"))
    config = spec.get("config", {})
    if not isinstance(config, dict):
        raise EditorError("__onesite__ 必须为 JSON 对象")
    lines = []
    if spec.get("docstring"):
        lines.append(spec["docstring"])
    if spec.get("table_name"):
        lines.append("__tablename__ = " + repr(spec["table_name"]))
    lines.append("__onesite__ = " + python_literal(config))
    names = set()
    for field in spec.get("fields", []):
        fname = identifier(field.get("name"))
        if fname in names or fname.startswith("__"):
            raise EditorError(f"字段名重复或为保留名称：{fname}")
        names.add(fname)
        annotation = expression(field.get("type"))
        kwargs = copy.deepcopy(field.get("kwargs", {}))
        if not isinstance(kwargs, dict) or not isinstance(field.get("props", {}), dict):
            raise EditorError(f"{fname}: Field 参数和 site_props 必须为对象")
        if field.get("props"):
            try:
                if "sa_column" in kwargs:
                    column = ast.parse(kwargs["sa_column"], mode="eval").body
                    if (
                        not isinstance(column, ast.Call)
                        or not (
                            (isinstance(column.func, ast.Name) and column.func.id == "Column")
                            or (
                                isinstance(column.func, ast.Attribute)
                                and column.func.attr == "Column"
                            )
                        )
                        or any(k.arg is None for k in column.keywords)
                    ):
                        raise ValueError("dynamic Column expression")
                    info_kw = next((k for k in column.keywords if k.arg == "info"), None)
                    info = ast.literal_eval(info_kw.value) if info_kw else {}
                    info["site_props"] = {**info.get("site_props", {}), **field["props"]}
                    value = ast.parse(python_literal(info), mode="eval").body
                    if info_kw:
                        info_kw.value = value
                    else:
                        column.keywords.append(ast.keyword(arg="info", value=value))
                    kwargs["sa_column"] = ast.unparse(column)
                else:
                    column_kwargs = ast.literal_eval(kwargs.get("sa_column_kwargs", "{}"))
                    info = column_kwargs.setdefault("info", {})
                    info["site_props"] = {**info.get("site_props", {}), **field["props"]}
                    kwargs["sa_column_kwargs"] = python_literal(column_kwargs)
            except (ValueError, TypeError, AttributeError, SyntaxError) as exc:
                raise EditorError(
                    f"{fname}: SQLAlchemy 元数据包含动态表达式，请在源码中的 info 内配置 site_props。"
                ) from exc
        value = field.get("value")
        if value is not None:
            if kwargs or field.get("props"):
                raise EditorError(f"{fname}: 清除自定义赋值后才能配置 Field 参数。")
            suffix = " = " + expression(value) if value else ""
        else:
            pairs = [f"{identifier(k)}={expression(v)}" for k, v in kwargs.items()]
            suffix = " = Field(" + ", ".join(pairs) + ")"
        lines.append(f"{fname}: {annotation}{suffix}")
    if spec.get("extra", "").strip():
        lines.append(textwrap.dedent(spec["extra"]).strip())
    if spec.get("hooks", "").strip():
        lines.append(textwrap.dedent(spec["hooks"]).strip())
    source = (
        spec.get("prefix", MODEL_IMPORTS).rstrip()
        + "\n\n\nclass "
        + name
        + ("(SQLModel, table=True):\n" if spec.get("table", True) else "(SQLModel):\n")
        + textwrap.indent("\n\n".join(lines), "    ")
        + "\n"
        + spec.get("suffix", "")
    )
    check_python(source, f"{name}.py")
    return source
