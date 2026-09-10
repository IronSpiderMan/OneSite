# OneSite

[English README](README.md) · [设计原则](docs/design-principles.md)

OneSite 是一个模型驱动的全栈代码生成 CLI。开发者维护 `app/models/` 中的 SQLModel；执行 `site sync` 后，在 `generated/` 中自动生成 FastAPI 的 Schema、CRUD、Service、REST API，以及 React/Vite 的页面、服务、菜单、国际化和主题资源。

## 安装与快速开始

要求 Python 3.10+；生成前端还需要 Node.js/npm；容器部署可选 Docker 或 Podman。

```bash
pip install onesite
site create inventory
cd inventory

# 在 app/models/ 中定义或修改 SQLModel
site sync --install
site run
```

开发本仓库时使用锁定的工具环境：

```bash
uv sync --group dev
uv run pytest
uv run ruff check src/onesite src/onesite_runtime tests
```

- 前端：`http://localhost:5173`
- API 文档：`http://localhost:8000/docs`
- 初始管理员：`admin@example.com` / `admin`（上线前必须修改）

日常循环是：修改 `app/models/`、`app/integrations/`、`app/utils/`、`app/resources.py` 或 `site_config.py` → `site sync` → 在 `/docs` 和前端验证。`generated/` 下的内容都是可重新生成的产物，不应作为唯一业务源码。项目统一使用 `app/` 与 `generated/` 布局，顶层 `models/`、`backend/`、`frontend/` 不受支持。

## 本地可视化编辑器

运行 `site web`（源码开发环境可用 `.venv/bin/site web`），访问
`http://127.0.0.1:8765`。可在网页中创建 `projects/<项目名>`、设计模型与字段、配置
`__onesite__` / `site_config.py`、编写 Hook，并执行 Sync / Run 和查看日志。
界面全部使用 Arco Design 组件，风格与 OneSite 的 Arco 主题一致。
也可继续运行独立的 `python webui.py`，不需要前端构建或连接 CDN。详见 [WebUI 使用说明](docs/webui.md)。

## 数据库迁移

使用 Alembic 管理数据库结构：空库执行 `site db revision -m "initial"` 后检查迁移并运行 `site db upgrade`；旧库先用与现有结构匹配的模型执行 `site db baseline`。迁移源文件位于 `app/migrations/`，会随同步复制到部署目录。参见 [迁移、权限和同步说明](docs/database-migrations.md)。

## 内置 Agent

在 `site_config.py` 中配置 `agents`（也支持同结构 JSON），执行 `site sync --install`，即可生成兼容 OpenAI 接口的异步 Agent、按用户隔离的会话/消息表，以及 `/agent` 对话页面。

```python
from onesite.config import AgentConfig, SiteConfig

config = SiteConfig(agents={
    "assistant": AgentConfig(
        title="数据助手",
        base_url="http://localhost:18080/v1",
        api_key_env="AGENT_API_KEY",
        model="your-model-name",
        roles=["admin", "developer"],
        model_tools={"User": ["list", "get"]},
        max_steps=20,
        timeout_seconds=120,
    )
})
```

在后端运行环境或工作目录的 `.env` 中设置 `AGENT_API_KEY`；本地服务不校验密钥时可以使用字符串 `None`。把地址和模型名称替换为实际服务配置，再执行 `site run`，从菜单进入智能助手。

- 按模型开放指定接口：`crud` 展开为 `list/get/create/update/delete`，可额外配置 `bulk_delete`。工具继续遵守当前用户的 API 和字段权限。
- 在 `app/agent_tools/` 编写异步自定义工具，在 `app/agent_hooks.py` 编写 Hook。支持 `before_run`、`before_model`、`before_tool`、`after_tool`、`after_run`、`on_error` 六个执行点。
- 对话自动保存，支持搜索历史、查看工具调用、停止执行，以及删除对话及其消息。运行中的对话需先停止再删除；删除对话不会撤销工具已经修改的业务数据。
- 内置执行超时和步数限制；中断的写操作不会自动重放。页面通过轮询按完整消息更新。

完整配置、自定义工具、Hook 示例和表结构见 [Agent 使用说明](docs/agents.md)。

## 应用资源生命周期

HTTP 客户端、连接池、设备 SDK 句柄等进程级资源可以放在 `app/resources.py`。新项目会自动创建该文件；已有项目首次执行 `site init` 或 `site sync` 时也会补齐。两个钩子都是异步函数，并接收 FastAPI 应用，因此可通过 `app.state` 保存资源：

```python
from fastapi import FastAPI
from httpx import AsyncClient

async def init_resources(app: FastAPI) -> None:
    app.state.http = AsyncClient()

async def destroy_resources(app: FastAPI) -> None:
    await app.state.http.aclose()
```

`site sync` 会把该文件同步到生成后端，并由 `main.py` 的 FastAPI `lifespan` 调用：OneSite 内置基础设施启动后执行初始化，内置基础设施关闭前执行销毁。请保留 `init_resources`、`destroy_resources` 函数名和 `app` 参数，生成时会校验其签名。

### 外部资源 Provider

一个 Provider 表示一个外部系统，可以管理多类资源；每类资源对应一个模型：

```python
class Camera(SQLModel, table=True):
    __onesite__ = {
        "external_resource": {
            "provider": "edgeflow",
            "resource": "cameras",
            "identity": "id",  # 可省略，默认 id
        }
    }
```

在 `site_config.py` 注册 Provider 模块：

```python
config = SiteConfig(
    ...,
    providers={
        "edgeflow": ExternalResourceProviderConfig(module="edgeflow")
    },
)
```

首次执行 `site sync` 会创建开发者维护的 `app/providers/edgeflow.py`。Provider 实现
`create(resource, payload)`、`update(resource, payload, previous)`、
`delete(resource, payload)` 和 `reconcile(desired)`。External Resource CUD
作为框架隐藏的事务内 `on_after_*` 钩子执行；Provider 失败会回滚本地变更。后端定时按
Provider 全局扫描并修复超时、进程中断或外部漂移造成的不一致。`external-resources`
管理页展示 Provider 级健康状态和汇总计数。

`resource_type`、`identity_field` 仍作为字段别名兼容。

## 命令

| 命令 | 作用 |
| --- | --- |
| `site init` | 在当前目录初始化配置、基础模型和图标参考页。 |
| `site create <项目名>` | 创建全栈项目。 |
| `site sync [-i/--install]` | 同步模型并生成代码；`-i` 会安装依赖。 |
| `site sync --build-cmd` | 同步代码，并构建命令项目到 `generated/backend/bin/`。 |
| `site run [项目路径] --component backend\|frontend\|all` | 启动后端、前端或两者。 |
| `site build [-c backend\|frontend\|all] [-e docker\|podman] [-t 标签] [-p 端口]` | 构建镜像并生成 `deploy/docker-compose.yml`。 |
| `site build --component desktop` | 为当前 macOS 或 Windows 平台构建原生 Tauri 客户端。 |
| `site compose [--engine docker\|podman] up -d` | 使用 `deploy/docker-compose.yml` 执行 Compose；也支持 `down`、`logs -f`。 |

`backend`/`frontend` 是 `--component` 选项值，正确写法是 `site run --component backend`，不是 `site run backend`。

### 命令行可执行文件

开发者维护的命令项目可放在 `app/cmd/<项目名>/`。macOS/Linux 项目提供
`build.sh`，Windows 项目提供 `build.bat`。执行 `site sync --build-cmd` 时，
OneSite 会在每个项目目录中运行当前平台对应的构建脚本，并要求脚本在该目录
生成 `<项目名>`（或 `<项目名>.exe`），随后将其复制到
`generated/backend/bin/`。没有当前平台构建脚本的项目会被跳过；普通
`site sync` 不会执行这些构建，因此不会拖慢日常同步。

## 模型、主键与关联

普通自增主键：

```python
from typing import Optional
from sqlmodel import Field, SQLModel

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    price: float = 0
```

这种 `id` 由数据库生成，创建接口默认不会接收它。若 `id` 是设备名、编码等业务主键，可显式授予字段创建权限：

```python
class Device(SQLModel, table=True):
    id: str = Field(
        primary_key=True,
        nullable=False,
        sa_column_kwargs={"info": {"site_props": {"permissions": "rcu"}}},
    )
    name: str
```

此时创建请求可以传 `id`；生成的读 Schema、路径参数、CRUD/Service 和前端客户端也都会使用 `str` 类型。常规更新接口不允许修改主键。

外键使用 `{目标}_id` 和 `foreign_key`：

```python
category_id: Optional[int] = Field(default=None, foreign_key="category.id")
```

生成的界面会显示关联对象标签并提供选择器。多对多中间表增加 `__onesite__ = {"is_link_table": True}`；只有关联键时会生成多选控件，包含额外字段时还会保留独立 CRUD。

需要在创建父记录时同时创建子记录，可在子模型外键的 `site_props.reverse`
中使用 `{"editor": "inline", "layout": "table"}`。`table` 布局与
`dict[str, SubModel]` 的结构化表格 UI 一致，但子项仍保存为独立数据库记录；
`on_remove` 可设为 `delete`（默认）或在可空外键上使用 `nullify`。

## 配置与权限

推荐在 `site_config.py` 中使用带类型的 `SiteConfig`；旧项目的 `site_config.json` 仍然兼容。两种格式都支持 `project_name`、`database_url`、`upload_dir`、`secret_key`、`allowed_origins`、`style`、`radius`、`navigation` 等配置。`navigation` 是按数组顺序排列的侧边栏树：`model` 引用模型的 `module_name`，`group` 是没有路由的可折叠二级菜单，`builtin` 支持 `dashboard`、`reports`、`external-resources` 和 `task-center`。分组标签须同时提供 `zh`、`en`；模型本身的权限和 `visible` 仍决定子项是否显示，空分组会自动隐藏。显式配置 `navigation` 后，未列出的模型仍可通过路由和 API 访问，但不会出现在侧边栏。`extra` 下的所有键值都会同步到后端 `.env`；可通过 `extra={"TIMEZONE": Timezone.ASIA_SHANGHAI}` 设置系统时区，也可继续使用任意有效的 IANA 时区字符串。它默认使用上海时区，并控制前端默认时间显示与 APScheduler 的 cron 调度；写入数据库的 datetime 会统一转换为 UTC。`Timezone` 内置了常见时区，使用 `postgres_url(host, port, user, password, db, params)` 可安全拼装并编码 PostgreSQL 连接地址。内置结构主题：`normal`、`industrial`、`neuron`。`style` 是构建时主题，执行 `site sync` 时会选择对应主题目录下的列表、详情、创建、仪表盘、设置、个人资料、单例页和 CSS 模板；缺少覆盖模板时回退到公共模板。`normal` 通过生成的兼容适配层使用 Ant Design 6，并且只有 normal 构建会增加 `antd` 依赖；明暗模式会同步到 Ant Design 的主题算法。生产环境务必更换 `secret_key`、数据库地址和跨域来源。

模型级选项写入 `__onesite__`：

`__onesite__` 也支持带编辑器自动补全和运行时校验的 Pydantic 配置；原有字典写法继续兼容：

```python
from onesite.config import OneSiteConfig

class Product(SQLModel, table=True):
    __onesite__ = OneSiteConfig(
        icon="Package",
        permissions={"user": "r", "admin": "crud", "developer": "crud"},
        edit_mode="drawer",
    )
```

- `translations`、`icon`：中英文文案和菜单图标。
- `permissions`、`visible`：接口 CRUD 权限和菜单可见性。
- `owner_field`：用户只能访问自己拥有的数据。
- `is_link_table`、`is_singleton`、`frontend_only`、`page_edit`：关系、单例、纯前端和编辑页行为。
- `actions`、`importable`、`exportable`、`import_key`：自定义操作与 CSV 导入导出。

### 模型自助报表

模型通过 `reports` 开放报表大类和可用字段；基础折线、平滑折线、面积图等具体样式
由用户在生成的报表页面选择，不写入模型配置。推荐使用带类型的 Pydantic 写法：

```python
from onesite.config import (
    OneSiteConfig,
    ReportDimensionInput,
    ReportInputs,
    ReportMeasureInput,
    ReportsConfig,
)

class Order(SQLModel, table=True):
    __onesite__ = OneSiteConfig(
        reports=ReportsConfig(
            categories=[
                "cartesian", "multi_cartesian", "composition", "scatter",
            ],
            inputs=ReportInputs(
                x={
                    "created_at": ReportDimensionInput(
                        bins=["none", "auto", "hour", "day", "week", "month"]
                    ),
                    "amount": ReportDimensionInput(),
                },
                y={
                    "amount": ReportMeasureInput(
                        aggregations=["raw", "sum", "avg", "min", "max", "median"]
                    ),
                    "quantity": ReportMeasureInput(
                        aggregations=["raw", "sum", "avg", "min", "max"]
                    ),
                },
                cls=["status", "channel"],
                count=["$rows", "id"],
            ),
            filters=["created_at", "status", "channel"],
            visible=["admin", "developer"],
        )
    )
```

字典写法使用相同结构。四个大类分别为：

- `cartesian`：单系列折线、平滑折线、面积、柱状、阶梯折线和柱线组合；
- `multi_cartesian`：按 `cls` 拆分的多折线、多面积、分组/堆叠柱状和多柱线组合；
- `composition`：饼、环、半环和南丁格尔玫瑰图；
- `scatter`：基础散点和分类散点。

`x` 配置可用分桶，`y` 配置可用聚合，`cls` 配置分类字段，`count` 配置可计数
字段。内置 `$rows` 表示 `COUNT(*)`。后端会再次校验图表所属大类、输入数量、字段、
分桶、聚合、筛选、字段读取权限和模型 owner scope。当前报表输入仅支持模型直接字段；
关联字段路径将在查询规划器支持显式 JOIN 后开放。

### 函数式 Action

需要自定义 Python 业务逻辑时，可以直接在 SQLModel 中使用 `@action`。
方法运行在数据库事务内，可按名称声明 `context`、`session` 或
`current_user` 参数：

```python
from onesite_runtime import ActionContext, ActionState, action

class Dataset(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    status: str = "draft"
    is_enabled: bool = False

    @action(permissions="da", label="切换状态", unavailable="disable")
    def toggle_enabled(self, *, context: ActionContext):
        self.is_enabled = not self.is_enabled

    @toggle_enabled.available
    async def can_toggle_enabled(self, *, session, current_user):
        if self.status != "draft":
            return ActionState(
                visible=True,
                enabled=False,
                reason="只有草稿状态可以修改",
            )
        return True
```

`available` 方法可以返回 `bool`、`None` 或 `ActionState`。动态条件由后端
计算，列表页通过一次批量请求获取当前页所有按钮状态；真正执行 action
时后端会再次检查，不能通过手工请求绕过条件。`unavailable="hide"`（默认）
会隐藏返回 `False` 的按钮，`"disable"` 则保留禁用按钮。`available` 可能被
重复调用，因此不应在其中修改数据或触发外部副作用。

只依赖当前记录字段的简单条件可以继续使用声明式写法，前端会即时判断，
后端也会再次校验：

```python
@action(condition={"field": "status", "op": "eq", "value": "draft"})
def publish(self):
    self.status = "published"
```

`condition=` 和 `@method.available` 不能同时配置。原有配置式 action 仍然
兼容，包括同时使用 `toggle` 和 `condition`：

```python
__onesite__ = {
    "actions": {
        "toggle_enabled": {
            "toggle": "is_enabled",
            "permissions": "da",
            "condition": {"field": "status", "op": "eq", "value": "draft"},
        },
    },
}
```

`importable` / `exportable` 也支持对象配置。M2M 只有显式配置后才会参与，
多个值使用 `;` 分隔；导入时，外键和 M2M 对应的对象必须已经存在。

```python
__onesite__ = {
    "import_key": "sku",
    "exportable": {
        "fields": ["sku", "name", "category_id"],
        "foreign_keys": {"category_id": "title"},
        "m2m": {"tags": "title"},
    },
    "importable": {
        "fields": ["sku", "name", "category_id"],
        "foreign_keys": {"category_id": "title"},
        "m2m": {"tags": "title"},
    },
}
```

上例会把 `category_id` 导出为 `Category.title`，把 `tags` 导出为
`标签一;标签二`；导入时执行反向查找。`import_key` 命中已有记录时覆盖，
否则创建新记录。字段的 `site_props` 可设置 `importable=False` 或
`exportable=False`，即使模型级 `fields` 包含该字段也会排除。

配置任一导入、导出、仪表盘工具或定时任务后，`site sync` 会自动生成统一的
“任务中心”页面。页面展示提交到进程内任务队列的导入、导出、工具和定时任务，
支持按类型、任务名称和状态筛选，并展示进度、时间、结果、错误及下载地址。
用户主动发起的任务按当前登录用户隔离；定时任务按照其手动执行权限展示。
刷新页面或错过 WebSocket 通知后仍可恢复状态。完成或失败的任务记录及其托管的
上传和下载文件保留 24 小时；应用启动时会清理一次，之后每 5 分钟清理一次。
旧的同步 CSV 导入 API 仍可通过
不传 `background=true` 保持原行为。
同步和后台导入都会要求模型级创建、更新权限；标准 CSV 导入还会逐行执行
字段权限校验，并为非管理员强制套用模型配置的 owner 范围。

可使用精确的 `kind` 与 `name` 组合让指定任务不出现在任务中心的列表和详情接口中。
隐藏只影响任务中心：任务仍会执行、落库、发送通知，并遵循相同的 24 小时保留策略。

```python
from onesite.config import HiddenTask, SiteConfig, TaskCenterConfig

config = SiteConfig(
    task_center=TaskCenterConfig(hidden=[
        HiddenTask(kind="tool", name="internal_cleanup"),
        HiddenTask(kind="scheduled_task", name="heartbeat"),
        HiddenTask(kind="import", name="audit_log"),
        HiddenTask(kind="export", name="audit_log"),
    ]),
)
```
自定义格式的导入 hook 需要自行执行内容级权限校验：通过可选的 `context`
参数读取 `context.current_role` 来过滤字段，并使用
`context.scoped_owner_id` 强制或验证 owner。生成的入口仍会在排队前要求模型级
创建和更新权限，但 OneSite 无法自动解析任意文件格式中的字段。
- `refresh_interval`：自动刷新。模型内的 `visualize` 已弃用，旧配置暂时兼容；
  新图表统一写在项目根目录的 `visualizations.py`：

```python
from onesite.visualization import chart, count, dim, line, metric, pie

visualizations = [
    chart(
        "sales_by_channel",
        title="各渠道销售趋势",
        preset=line.stacked_area_gradient,
        model="Order",
        x=dim("created_at", bucket="day"),
        series=dim("channel"),
        y=metric("amount", aggregate="sum", label="销售额"),
    ),
    chart(
        "orders_by_status",
        title="订单状态分布",
        preset=pie.rounded_donut,
        model="Order",
        category=dim("status"),
        value=count(),
    ),
]
```

预设按图表类型提供可自动补全的常量，例如 `line.smooth`、
`line.stacked_area_gradient` 和 `pie.rounded_donut`；原有字符串写法继续兼容。

图表固定条件可使用相对时间范围。例如仅统计今日告警：

```python
where={"created_at": {"period": "today"}}
```

支持 `today`、`yesterday`、`this_week`、`last_week`、`this_month`、`last_month`。
该条件只能用于 `date` 或 `datetime` 字段，按系统时区计算。

  同一输入契约可以切换不同预设。当前支持折线/面积/堆叠面积、基础与分类散点、
  饼/环/半环、热力、雷达、树/矩形树/旭日和桑基图。字段路径如
  `category.name` 会沿外键自动关联；同步时会检查输入完整性、字段类型、聚合、
  权限和布局。完整设计见 `docs/visualization-redesign.md`。
- `dashboard_metrics`：在 Dashboard 顶部生成聚合指标卡。和图表一样，KPI
  声明放在项目根目录的 `visualizations.py`，并通过 `model` 指定数据来源。
  支持 `count`、`sum`、`avg`、`min`、`max`、`distinct_count`，固定过滤、时间周期和上一周期环比：

```python
from onesite.visualization import dashboard_metric

dashboard_metrics = [
    dashboard_metric(
        "total_orders",
        model="Order",
        title="订单总数",
        aggregation="count",
    ),
    dashboard_metric(
        "paid_revenue_today",
        model="Order",
        title="今日成交额",
        field="amount",
        aggregation="sum",
        where={"status": "paid", "created_at": {"period": "today"}},
        compare="previous_period",
        format={"type": "currency", "currency": "CNY", "decimals": 2},
        visible=["admin", "developer"],
        icon="Wallet",
        color="green",
        link="/orders?status=paid",
    ),
]
```

相对时间范围支持 `today`、`yesterday`、`this_week`、`last_week`、`this_month`、`last_month`、`last_7_days`、`last_30_days`。指标角色范围会和模型读取权限取交集，后端不会向无权限角色返回指标。旧的 `time_field + period` 与 `__onesite__.dashboard_metrics` 暂时兼容；后者会在 `site sync` 时提示迁移。
- `is_notification_table`、`time_series_table`：通知/WebSocket 与时序表配置。
权限分三层：模型级 `c/r/u/d`，字段级 `c/r/u`，以及 `visible` 菜单可见性。角色由低到高为 `user`、`admin`、`developer`。字段权限未配置时会继承模型权限（移除 `d`）；默认 `id` 隐藏、`created_at` 只读、`updated_at` 可读写。用字段 `site_props.permissions` 显式配置即可覆盖默认值。

字段 `site_props` 还支持 `is_search_field`、`component`（`image`/`images`/`file`/`textarea`/`json`/`location`）、`create_optional`、`update_optional`、`reverse_display`、`allow_download`、`group`、`fixed_keys`、`lock_keys` 等。

结构化 JSON 子字段支持条件显示、条件必填和隐藏后清理。条件键默认引用 JSON
内部的同级字段；使用 `$root.<字段名>` 可以引用所属 SQLModel 记录的顶层字段：

```python
def only_for(kind: str):
    return {"info": {"site_props": {
        "visible_when": {"$root.type": [kind]},
        "clear_when_hidden": True,
    }}}

class Properties(SQLModel):
    a: str | None = Field(default=None, sa_column_kwargs=only_for("none"))
    b: str | None = Field(default=None, sa_column_kwargs=only_for("none"))
    c: str | None = Field(default=None, sa_column_kwargs=only_for("password"))
    d: str | None = Field(default=None, sa_column_kwargs=only_for("password"))

class Connector(SQLModel, table=True):
    type: str
    properties: Properties = Field(sa_column=Column(JSON))
```

如果字段显示时必须有值，可再配置相同条件的 `required_when`。生成的创建、编辑、
详情页面会即时应用规则，API schema 也会重复执行隐藏字段清理和必填校验。
`$root` 引用的字段必须存在于所属模型中。

定位字段使用内置的 `Location` 值对象、JSON 列和 `location` 组件：

```python
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.location import Location


class Store(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    location: Optional[Location] = Field(
        default=None,
        sa_column=Column(
            JSON,
            nullable=True,
            info={"site_props": {"component": "location"}},
        ),
    )
```

生成的表单既可以手动输入经纬度，也可以通过“获取当前位置”按钮调用浏览器
Geolocation API，或展开 OpenStreetMap 地图点击选点。浏览器会请求用户授权；除
localhost 外，定位功能通常要求 HTTPS。现有项目需要执行一次 `site sync -i` 安装
Leaflet 依赖。
地图默认使用 OpenStreetMap 官方瓦片地址；部署时可以通过前端构建环境变量
`VITE_MAP_TILE_URL` 和 `VITE_MAP_ATTRIBUTION` 切换瓦片服务。

## 通用前端 Feature 与自定义 Dashboard Widget

自定义 Feature 在 `SiteConfig.custom_features` 中声明。第一次执行 `site sync`
时，OneSite 会在 `app/frontend/` 和 `app/backend/` 下创建可安全运行的 page、
store、service、API 与 CRUD 源码；已有源码永不覆盖，之后每次同步只镜像到
`generated/`。

```python
from onesite.config import (
    CustomDashboardWidget,
    CustomFeature,
    CustomFeatureMenu,
    CustomOverride,
    CustomPage,
    SiteConfig,
)

feature = CustomFeature(
    name="operations",
    pages=[
        CustomPage(
            id="workspace",
            path="/operations",
            component="pages/Workspace.tsx",
            access=["admin", "developer"],
            menu=CustomFeatureMenu(
                title={"zh": "运营工作台", "en": "Operations"},
                icon="Activity",
            ),
        ),
        CustomPage(
            id="public_status",
            path="/public/status",
            component="pages/PublicStatus.tsx",
            layout="public",
        ),
    ],
    overrides=[
        CustomOverride(
            target="model.sync_task.detail",
            component="pages/CustomSyncTask.tsx",
        ),
    ],
    dashboard_widgets=[
        CustomDashboardWidget(
            id="health",
            component="components/HealthWidget.tsx",
            title={"zh": "运行健康度", "en": "Operations Health"},
            span={"md": 12, "xl": 6},
            access=["admin", "developer"],
        ),
    ],
    dependencies={"dayjs": "^1.11.0"},
)

config = SiteConfig(custom_features=[feature])
```

默认同时创建前后端。`frontend_only=True` 只创建前端，并提供返回空数据的本地
service；`backend_only=True` 只创建 API、service 和 CRUD。两个选项不能同时为
`True`。旧的 `app/frontend/features/*/feature.py` 声明格式不再支持。

默认的 `layout="app"` 路由会挂载在需要登录的生成应用外壳内，并支持通过
`access` 限制前端角色。`layout="public"` 路由位于应用外壳之外，不要求 token。
如果项目显式配置了导航树，可以通过带命名空间的 route ID 放置菜单入口：

```python
from onesite.config import NavGroup, NavRoute

NavGroup(
    key="operations",
    label={"zh": "运营", "en": "Operations"},
    children=[NavRoute(route="operations.workspace")],
)
```

生成路由提供稳定的替换目标，例如 `builtin.dashboard`、`builtin.settings`、
`model.device.list`、`model.device.detail` 和 `model.device.create`。Override
只替换页面组件，原 URL 与导航契约保持不变。同步时会校验 route ID、路径、组件
文件、菜单引用、角色声明及 override 目标。
前端 `access` 只控制导航与路由渲染；Feature 涉及的数据和操作仍必须由后端 API
权限作为真正的安全边界。

Widget 的最终 ID 为 `<feature>.<widget>`。生成的 Dashboard 会按照 `order`
排序、按当前角色过滤，并使用 12 列响应式布局。默认由当前主题提供标题和 Card
外壳；如果组件自行绘制完整容器，可设置 `frame=False`。

约定位置的 `locales/en.json` 与 `locales/zh.json` 会合并到
`features.<feature_name>` 命名空间，因此组件可以直接调用
`t('features.operations.status')`。Feature 声明的 npm 依赖会合并到生成的
`package.json`；依赖版本冲突会在同步时直接报错。

完整示例位于 `examples/datahub/app/frontend/features/ops_dashboard/`，包含登录内
多页面、公开页面、生成页面替换、两个 Dashboard Widget、共享 Zustand store、
service、多语言和固定模拟数据。

## MQTT 回调

MQTT Broker 参数和 Topic 绑定写在项目配置中；下面展示与旧版
`site_config.json` 兼容的结构，`site_config.py` 使用同名字段：

```json
{
  "mqtt": {
    "url": "mqtt://localhost:1883",
    "username": "admin",
    "password": "public",
    "client_id": "onesite_backend",
    "callbacks": [
      {
        "topic": "alarm-trigger/alarms/#",
        "handler": "on_alarm",
        "qos": 1
      }
    ]
  }
}
```

执行 `site sync` 时，OneSite 会查找
`app/integrations/mqtt/on_alarm.py`。目录或文件不存在时会自动生成：

```python
async def on_alarm(topic: str, payload: str):
    # TODO: Implement your business logic here
    pass
```

`app/integrations/mqtt/` 是开发者维护的唯一源码目录。每次同步都会将其中
的 Python 文件单向覆盖到 `generated/backend/app/integrations/mqtt/`，因此不要只在
后端副本中修改业务逻辑。OneSite 根据 callbacks 自动生成
`generated/backend/app/core/mqtt_bindings.py` 完成注册，handler 文件只需实现同名
函数，不需要自行调用 `register_handler`。

每项 callback 必须提供非空 `topic` 和合法的 Python 函数名 `handler`。
`qos` 可省略，默认值为 `1`，只允许 `0`、`1`、`2`。同一个 handler
可以绑定多个 Topic。生产环境建议通过 `MQTT_URL`、`MQTT_USERNAME`、
`MQTT_PASSWORD`、`MQTT_CLIENT_ID` 覆盖连接信息，避免把真实凭据提交
到仓库。

## 开发者工具模块

可复用的后端工具代码放在 `app/utils/`：

```text
app/utils/
├── __init__.py
├── formatting.py
└── data/
    └── defaults.json
```

执行 `site sync` 时，该目录会递归同步到
`generated/backend/app/utils/`。开发源码会覆盖生成目录中的同名文件；
源码中已删除的文件也会从生成目录清理。缺少 `__init__.py` 时会自动创建，
`__pycache__` 和 `.pyc` 文件不会同步。后端代码可通过下面的方式导入：

```python
from app.utils.formatting import format_alarm
```

项目工具函数应放在 `app/utils/`，会同步到 `generated/backend/app/utils/`。

### 自定义后端 API、Service 与 CRUD

自定义后端代码所需的 Python 包请写入
`app/requirements.extra.txt`，每行一个标准 pip 依赖。OneSite 会将其与
内置依赖去重后合并到生成的后端 `requirements.txt`，因此 `site sync --install`
和 Docker 构建都会安装这些依赖：

```text
boto3>=1.35
httpx>=0.27,<1
```

`site init` 和 `site create` 默认会创建这个空文件。请在 `app/` 中维护它，
不要直接编辑每次同步都会覆盖的
`generated/backend/requirements.txt`。

开发者维护的后端模块放在 `app/backend/api/`、`app/backend/services/` 和
`app/backend/cruds/`。执行 `site sync` 后，它们会分别镜像到：

```text
generated/backend/app/api/endpoints/custom/
generated/backend/app/services/custom/
generated/backend/app/cruds/custom/
```

只有 `SiteConfig.custom_features` 声明的后端模块会注册。首次同步会为完整模式或
`backend_only` Feature 创建带顶层 `router` 的模块；之后 prefix、tag、依赖和实现
均由开发者维护：

```python
from fastapi import APIRouter

from app.services.custom.health import get_health

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health():
    return get_health()
```

未配置的辅助模块只复制、不会注册为 API。删除源文件后，
下次同步也会删除对应的生成副本。自定义 Service 与 CRUD 的导入路径分别为
`app.services.custom.*` 和 `app.cruds.custom.*`。

## 已生成能力

- JWT 登录、角色权限、所有者隔离
- CRUD、唯一性校验、列表检索与筛选
- 图片/文件上传、JSON 与嵌套 Pydantic 编辑器
- 外键标签、多对多、树结构、单例配置页
- 自定义按钮、CSV 导入导出、通知中心和 WebSocket
- 自动刷新、统计图表、APScheduler 定时任务
- EN/ZH 国际化、六套结构主题
- Docker/Podman、Compose 与可选 TimescaleDB 时序能力

## 部署与目录

### 桌面客户端

`site sync` 会在 `generated/frontend/src-tauri` 生成 Tauri 2 桌面外壳。
先在项目配置中设置桌面客户端访问的 FastAPI 地址；下面展示与旧版
`site_config.json` 兼容的结构，`site_config.py` 使用同名字段：

```json
{
  "desktop": {
    "identifier": "com.example.inventory",
    "version": "1.0.0",
    "api_url": "https://api.example.com/api/v1",
    "width": 1280,
    "height": 800
  }
}
```

`desktop.api_url` 必须是绝对 HTTP(S) 地址；打包后的客户端不能使用 Vite
开发代理。同步时会将 macOS 和 Windows 的 Tauri 精确来源加入后端 CORS。

```bash
site sync --install
site build --component desktop
```

macOS 当前平台会生成 `.app` 和 `.dmg`，Windows 当前平台会生成 NSIS
安装程序，不进行跨平台交叉编译。macOS 需安装 Rust 和 Xcode Command Line
Tools；Windows 需安装 Rust MSVC 工具链、Microsoft C++ Build Tools 和
WebView2。产物位于
`generated/frontend/src-tauri/target/release/bundle/`。

### 容器部署

```bash
site build --engine docker --tag v1 --port 3000
site compose up -d
site compose logs -f
```

`site build` 会生成 `deploy/docker-compose.yml`；`site create`、`site init` 和 `site sync` 会确保 `deploy/.env.example` 存在。部署时可复制为 `deploy/.env` 并填写环境差异，`site compose` 会自动加载它。若 `database_url` 以 `postgresql` 开头，会加入 PostgreSQL 服务。项目的开发源码位于 `app/models/`、`app/integrations/` 和 `app/frontend/`；可重新生成的后端、前端与各自的 Dockerfile 位于 `generated/backend/` 和 `generated/frontend/`。

生成的后端 Dockerfile 默认使用清华 TUNA PyPI 镜像，并在安装依赖前升级
pip、setuptools、wheel，同时增加超时和重试次数，以适应较慢的容器网络。
生产构建在 Python builder 阶段使用 Nuitka 编译，最终使用不包含 Python
解释器的 `debian:bookworm-slim` 运行 standalone 产物，并从 builder
复制系统 CA 证书以支持对外 HTTPS 请求。

```text
项目根目录/
├── app/
│   ├── models/                  # 开发者维护的数据模型
│   ├── integrations/
│   │   └── mqtt/                # 开发者维护的 MQTT handler
│   ├── backend/
│   │   ├── api/                 # 配置声明的自定义 Feature APIRouter
│   │   ├── services/
│   │   └── cruds/
│   └── utils/                   # 开发者维护的后端工具模块
├── generated/
│   ├── backend/
│   │   ├── Dockerfile
│   │   └── app/                 # 生成的 FastAPI 应用
│   └── frontend/
│       ├── Dockerfile
│       ├── src-tauri/            # 生成的 Tauri 2 桌面外壳
│       └── src/                 # 生成的 React/Vite 应用
├── deploy/
│   ├── .env.example
│   ├── .env                     # 可选，本地创建且不会提交
│   └── docker-compose.yml       # site build 时生成
├── site_config.py
└── icon-reference.html
```

更多设计背景请阅读 [设计原则](docs/design-principles.md)，并参考 `examples/`。
