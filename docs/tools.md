# Python 类工具

工具定义放在 `app/tools/`，在 `site_config.py` 中显式注册。输入和结果使用
Pydantic 模型，同一份声明用于生成表单、后端校验和结果展示。

```python
from onesite.config import SiteConfig
from app.tools.text_transform import TextTransformTool

config = SiteConfig(tools=[TextTransformTool])
```

完整示例见 [examples/typed_tools](../examples/typed_tools/app/tools/text_transform.py)。
进入示例目录运行 `site sync`，然后运行 `site run all`。默认只有 admin 和
developer 可以执行工具。

## 定义工具

```python
from pydantic import BaseModel, Field
from onesite_runtime.tools import BaseTool, ToolContext

class Inputs(BaseModel):
    text: str = Field(min_length=1)

class Result(BaseModel):
    content: str

class UppercaseTool(BaseTool):
    name = "uppercase"
    title = "Uppercase"
    description = "Convert text to uppercase."
    permissions = ("admin", "developer")
    inputs = Inputs
    result = Result

    async def run(self, inputs: Inputs, context: ToolContext) -> Result:
        return Result(content=inputs.text.upper())
```

- `name` 是稳定的工具标识，必须为合法 Python 标识符；`title` 必填。
- `inputs` 和 `result` 都必须是 Pydantic 对象模型。无参数或无业务结果时可使用空模型。
- `run` 必须是异步方法，接受 `inputs` 和 `context`。每次执行创建独立工具实例，
  构造函数应无必填参数。
- 工具类必须直接定义在 `app/tools/` 的模块中，支持子包和共享模型模块。
- 工具模块会在 `site sync` 时导入；数据库等运行依赖放在执行方法中，或通过
  `context.session` 获取。

保留原始模型及其 `field_validator`、`model_validator`。请求校验失败返回 422，
任务不入队；返回结果校验失败时任务标记失败，具体错误写入后端日志。输入会在
请求和队列消费两个边界校验，校验器应无副作用且支持重复验证。

## 字段与表单

| Pydantic 类型 | 默认控件 |
| --- | --- |
| `str` | 文本框 |
| `int`、`float` | 数字输入框 |
| `bool` | 复选框 |
| `Literal`、`Enum` | 下拉选择 |
| `list[Enum]` | 多选 |
| `date`、`datetime` | 日期、时间选择 |
| 嵌套模型 | 分组表单 |
| `list[T]` | 可增删列表 |
| `dict`、`Any` | JSON 编辑器 |
| `InputFile`、`list[InputFile]` | 文件上传 |

`Field(title=..., description=...)` 设置默认文案。`Field()` 中的约束由后端执行，
可表达为 HTML 约束的部分也用于前端提示。通过 `json_schema_extra.site_props`
补充 UI 和上传配置：

```python
text: str = Field(
    min_length=1,
    json_schema_extra={
        "site_props": {"component": "textarea", "placeholder": "Enter text"},
    },
)
```

`component="json"` 可将嵌套对象或列表切换为 JSON 编辑器。必填性遵循 Pydantic：
`value: str | None` 必填且允许 null；`value: str | None = None` 允许省略。
表单通过“使用默认值”省略字段，通过“设为空值”显式提交 null。`default_factory`
在请求校验时运行，生成代码时不会调用。数字枚举保留数字类型，false、0、空字符串
和 null 都不会被合并成“缺失”。

支持普通字符串字段别名。复杂联合类型（除 `T | None`）、递归模型、RootModel、
AliasChoices/AliasPath 暂不支持，会在同步时报告具体位置。

## 国际化

工具级别使用 `translations`，支持 `title`、`description`、`execute_label`：

```python
translations = {
    "zh": {"title": "文本转换", "description": "处理文本", "execute_label": "开始处理"},
}
```

输入和结果模型使用现有 `__i18n__` 约定：

```python
__i18n__ = {
    "zh": {
        "fields": {
            "text": {"title": "原文", "help": "需要处理的文本", "placeholder": "请输入"},
            "mode": "处理方式",
        },
        "enums": {"mode": {"upper": "大写", "lower": "小写"}},
    },
}
```

嵌套模型的翻译随模型复用。枚举也支持自己的 `__i18n__`，字段上的选项翻译优先。
翻译编入现有 en/zh 语言包；缺少翻译时使用 `Field` 或工具的默认文案。

## 结果展示

```python
from onesite_runtime.tools import ResultUI

result_ui = ResultUI(renderer="detail")
```

`detail` 默认按字段展示；`json` 显示原始 JSON。以下模式需要指定结果字段：

```python
result_ui = ResultUI(renderer="text", field="content")      # 字符串字段
result_ui = ResultUI(renderer="table", field="rows")        # 对象列表
result_ui = ResultUI(renderer="download", field="report")   # OutputFile 字段
```

进度、状态、执行错误由现有任务中心记录，业务结果由 `result` 模型定义。

## 文件输入和输出

```python
from pydantic import BaseModel, Field
from onesite_runtime.tools import InputFile, OutputFile

class Inputs(BaseModel):
    files: list[InputFile] = Field(
        min_length=1,
        max_length=5,
        json_schema_extra={"site_props": {"accept": [".txt"], "max_size_mb": 20}},
    )

class Result(BaseModel):
    report: OutputFile

# 在工具的 run() 中：
# path = context.output_path("report.txt")
# path.write_text("...", encoding="utf-8")
# return Result(report=context.output_file(path, content_type="text/plain"))
```

文件输入目前限定为顶层字段，文件类型、大小和数量在后端检查。`InputFile`
提供 `path`、`name`、`size`、`content_type`、`read_bytes()`、`read_text()`。
文件路径由服务端分配，不能通过 JSON 指定；输入历史中不暴露本地路径。
输出使用 `OutputFile`，通过 `context.output_file()` 登记当前任务输出目录中的文件。

## 执行配置和调用接口

```python
from onesite_runtime.tools import ExecutionOptions

execution = ExecutionOptions(timeout_seconds=120)
```

继续使用现有后台队列、超时、进度通知和任务中心。框架在提交和开始执行时检查
当前用户的角色权限。`context` 提供 `current_user`、`user_id`、`session`、
`set_progress()`、`run_sync()` 和输出目录方法。

无文件时可向 `POST /api/v1/tools/{name}/execute` 直接发送 JSON 对象。
有文件时使用 multipart：普通参数放入 `__inputs__` 字段的 JSON 对象，文件使用
对应输入字段名上传。成功返回 202 和 task_id；通过
`GET /api/v1/tools/executions/{task_id}` 查询进度和结果。

旧的 `Tool(...)`、`ToolInput(...)` 和独立 handler 函数继续兼容，可以与工具类
混合注册。生成后的工具运行时位于 `app/core/tool_types.py`，应用无需安装 OneSite。
