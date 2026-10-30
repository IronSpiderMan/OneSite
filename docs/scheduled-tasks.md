# Python 类定时任务

定时任务可以继承 `BaseScheduledTask`，使用 Pydantic 定义输入和结果模型。
APScheduler 继续负责 cron/interval 触发，业务通过现有后台队列执行：

```text
APScheduler → 校验输入并保存快照 → 入队 → run(inputs, context) → 校验结果
```

## 定义与注册

任务类放在 `app/tasks/`，在 `site_config.py` 中显式注册：

```python
from onesite.config import SiteConfig
from app.tasks.daily_summary import DailySummaryTask

config = SiteConfig(scheduled_tasks=[DailySummaryTask])
```

任务定义示例：

```python
from pydantic import BaseModel, Field
from onesite_runtime.tasks import (
    BaseScheduledTask, CronSchedule, ExecutionOptions,
    NotifyOptions, ScheduledTaskContext,
)

class Inputs(BaseModel):
    keep_days: int = Field(default=30, ge=1)

class Result(BaseModel):
    processed: int = Field(ge=0)

class CleanupTask(BaseScheduledTask):
    name = "cleanup"
    title = "Cleanup"
    description = "Clean expired records."
    inputs = Inputs
    result = Result
    schedule = CronSchedule(cron="0 3 * * *")
    enabled = False
    overlap = "skip"
    execution = ExecutionOptions(timeout_seconds=600)
    manual_permissions = ("admin", "developer")
    notify = NotifyOptions(on_failure=True, roles=["developer"])

    async def run(self, inputs: Inputs, context: ScheduledTaskContext) -> Result:
        # Implement the cleanup using context.session.
        return Result(processed=0)
```

也可使用 `IntervalSchedule(seconds=300)`。cron 是五段表达式，调度时区沿用项目
`extra["TIMEZONE"]`。框架为每次执行创建新实例；构造函数应无必填参数。

完整示例见 [examples/typed_tasks](../examples/typed_tasks)。进入示例目录运行
`site sync`、`site run all`，以 admin/developer 登录后，在 Dashboard 编辑参数、
手动执行或启用调度，在任务中心查看结构化结果。示例默认关闭自动调度。

## 参数与持久化

参数的优先级为：界面保存的覆盖值 → 任务类的 `defaults` → Pydantic 模型默认值。

```python
class CleanupTask(BaseScheduledTask):
    # Other declarations omitted.
    defaults = {"keep_days": 60}
```

界面展示模型推导出的嵌套表单、列表、枚举及约束，支持“使用默认值”和“设为空值”。
类型、必填性、字段别名、自定义校验器的规则与 [Tools](tools.md) 一致。

类任务更新接口的 `params` 是**完整的用户覆盖集合**，替换之前的覆盖集合。
例如 `{"params": {"keep_days": 10}}` 保存覆盖值；`{"params": {}}` 恢复声明默认值。
旧的函数任务继续保持原来的参数更新语义。

`tasks_state.json` 只保存用户覆盖值及可编辑的调度状态，不保存模型类、字段描述或
自动生成的默认值。因此后续模型调整不会被旧字段描述覆盖，`default_factory`
也不会被冻结。生成代码时不调用工厂；保存、启用、提交执行时的模型校验可能调用
工厂，但只有实际入队时生成的输入快照用于这次执行。

参数编辑先完成整体验证，再保存参数、描述和调度设置，校验失败返回 422。
启动时启用的任务若因缺少必填参数等原因无法通过校验，会停止自动调度并展示配置
错误；补齐参数后可重新启用。旧任务迁移为类任务时，已保存的参数值会转为覆盖值。

## 执行、权限与恢复

- `overlap="skip"`：同名任务已有排队或执行记录时，复用该记录。
- `overlap="queue"`：每次触发都入队，由现有队列依次执行。
- 重叠判断覆盖完整的后台执行周期；APScheduler 的 `max_instances` 仅作用于短暂的入队回调。
- 自动触发时 `context.trigger == "schedule"`，`requested_by` 和 `current_user` 为 `None`。
- 手动触发时附带当前用户，提交和开始执行时都检查 `manual_permissions`。
- 默认失败通知发送给 developer；通过 `NotifyOptions` 配置成功、失败通知与接收角色。

不要在自动任务中依赖某个默认管理员身份。需要用户身份的业务应显式建模，或在
`run()` 中根据触发方式处理。

输入模型在入队和消费时校验，结果模型在成功完成前校验，校验器应无副作用且支持
重复验证。超时和校验错误会记录为任务失败。重启时，执行中的任务标记中断，排队
任务使用原始输入快照恢复，保留动态默认值以及执行历史中排除的字段。

私有快照保存在执行记录的 `payload_json`，API 不返回它。未纳入 Alembic 的旧数据库
会在启动时自动补充该列；已纳入 Alembic 的项目应按现有流程执行
`site db revision -m "add task input snapshots"`，审阅后运行 `site db upgrade`。

## 国际化与结果展示

工具与任务共享 Pydantic 解析、输入控件、结果控件和基础运行时类型。任务标题和
描述使用 `translations`；输入、结果和嵌套模型使用 `__i18n__`。生成的语言包使用
`scheduled_task_definitions.<name>` 命名空间。

通过 `ResultUI(renderer="detail" | "json")` 展示完整结果，或指定字段：

```python
result_ui = ResultUI(renderer="text", field="content")
result_ui = ResultUI(renderer="table", field="rows")
result_ui = ResultUI(renderer="download", field="report")
```

文件结果使用共享 `OutputFile` 类型，通过当前任务的 `context.output_file(path)`
登记；文件必须位于 `context.output_dir` 下。无人值守任务的输入使用持久化资源 ID
或业务模型 ID，暂不支持 `InputFile` 上传输入。

旧的 `ScheduledTask(...)` 与 `app/tasks/` 中的独立异步 handler 可以继续使用，
也可以与类任务混合注册。生成后的应用无需安装 OneSite。
