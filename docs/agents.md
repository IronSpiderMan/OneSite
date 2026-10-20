# 内置 Agent

OneSite 可生成一个基于 `AsyncOpenAI` 的极简 Agent，使用兼容 Chat Completions 的模型接口。配置 `agents` 后运行 `site sync`，生成会话 API、内部数据表及 `/agent` 对话页面。无需 pi、Node Agent 服务或独立任务队列。

## 配置

推荐在 `site_config.py` 中使用类型化配置；`site_config.json` 支持相同字段。

```python
from onesite.config import AgentConfig, SiteConfig, env

config = SiteConfig(
    agents={
        "assistant": AgentConfig(
            title="数据助手",
            base_url=env(
                "AGENT_BASE_URL",
                default="http://100.114.83.111:18080/v1",
            ),
            api_key_env="AGENT_API_KEY",
            model=env(
                "AGENT_MODEL",
                default="Qwen3.8-27B-GGUF/Qwen3.8-27B-Q4_K_M.gguf",
            ),
            instructions="帮助用户查询和维护系统数据。",
            roles=["admin", "developer"],
            max_steps=20,
            timeout_seconds=120,
            user_input_timeout_seconds=1800,
            model_tools={
                "A": ["crud", "bulk_delete"],
                "B": ["list", "get"],
            },
            custom_tools=["recalculate"],
            require_confirmation=["cud", "bulk_delete", "import"],
            hooks={
                "before_run": "agent_hooks.inject_context",
                "before_tool": "agent_hooks.check_operation",
                "after_tool": "agent_hooks.sanitize_result",
            },
        )
    }
)
```

将 `A`、`B` 替换为项目中真实的 SQLModel 类名。`crud` 展开成 `list/get/create/update/delete`；第一版支持普通 CRUD 模型及只读模型的读取操作，不支持 singleton、通知或时序模型。

通过运行环境提供 `AGENT_API_KEY`，或放入后端工作目录的 `.env`。不校验密钥的本地服务可设置 `AGENT_API_KEY=None`。密钥不写入会话记录，也不返回前端。`timeout_seconds` 是整轮主动执行的超时，亦用于单次模型请求；等待用户填写或确认使用独立的 `user_input_timeout_seconds`（默认 1800 秒），不消耗执行时间；`max_steps` 限制每轮模型调用次数。

运行 `site sync` 时，这套全局 LLM 连接参数会像 Kafka/MQTT 参数一样同步到 `generated/backend/.env`，并在生成的 `app/core/config.py` 中声明为 `Settings` 字段。构建 Compose 部署后，也会作为后端容器的环境变量传入。可在 `deploy/.env` 覆盖：

```env
AGENT_BASE_URL=https://api.openai.com/v1
AGENT_MODEL=gpt-4.1-mini
AGENT_API_KEY=sk-...
```

`AGENT_BASE_URL` 和 `AGENT_MODEL` 分别覆盖配置中的 `base_url`、`model`，并由所有内置 Agent 共用。密钥变量名仍由 `api_key_env` 指定，因此上例使用默认的 `AGENT_API_KEY`。后续执行 `site sync` 会更新 URL 和模型的配置默认值，但不会清空已经填写的 API Key。

```bash
site sync --install
site run all
```

页面入口自动加入菜单，仅对至少有一个可用 Agent 的角色显示。每次工具执行都会重新读取用户角色，实际权限取 Agent 配置与用户权限的交集，内部 HTTP 调用继续执行原业务 API 的校验。创建、更新参数和读取结果进一步按字段角色权限过滤；记录 ID 按现有 API Schema 保留。

## 工具参数

工具名称为 `A_list`、`A_get`、`A_create` 等，参数 Schema 从运行中的 FastAPI OpenAPI 定义取得：

```python
A_get(id=1)
A_list(page=1, size=20)
A_create(body={"title": "Example"})
A_update(id=1, body={"title": "Updated"})
A_delete(id=1)
A_bulk_delete(body={"ids": [1, 2]})
A_import(file_content="title\nExample\n", file_name="data.csv", dry_run=False)
```

List 支持 API 暴露的查询参数，单页限制为 1～100 条。模型只能选择注册工具和提供参数，不能指定任意 URL 或身份。

`import` 需要加入 `model_tools`，且目标模型已配置 `importable`。Agent 将 `file_content`（最多 100 万字符的 UTF-8 文本）转换为 multipart 文件，调用现有导入 API；默认文件名为 `import.csv`，普通导入器使用 CSV，自定义导入器按其文本格式处理。支持 API 的 `dry_run`、`background` 参数，导入同时要求创建和更新权限。后台导入返回任务信息，表示任务已提交，不代表所有数据已导入。

## 用户确认

`AgentConfig.require_confirmation` 默认是 `False`，工具按原流程直接执行。需要确认时可以配置：

```python
# 所有模型的新增、修改、删除、批量删除和导入
require_confirmation=["cud", "bulk_delete", "import"]

# 仅指定操作或具体工具（包括自定义工具）
require_confirmation=["delete", "A_bulk_delete", "recalculate"]

# 所有写操作和自定义工具；list/get 不要求确认
require_confirmation=True
```

操作支持全名 `create/update/delete/bulk_delete/import/list/get` 和简写 `c/r/u/d`、`cud`、`crud`。列表中的操作名应用于该 Agent 的所有模型；具体工具名只匹配该工具。确认配置不会额外开放工具，仍需在 `model_tools` 或 `custom_tools` 中注册。

工具参数先经过 `before_tool` 和权限校验，再展示确认卡片。卡片包含工具名称、最终参数以及“确认执行 / 拒绝”按钮；确认只允许执行这一次调用，拒绝会向模型返回错误结果。批量调用逐个确认，模型不能通过工具参数或聊天中的“同意”代替按钮确认。确认后再次校验当前权限，Hook 不会重新修改已确认的参数。

确认与表单记录统一存入消息 `details.interactions`（兼容读取旧的 `details.confirmations`），刷新页面或 SSE 重连后仍可查看和处理。只有会话所有者能提交决定；重复提交、已停止、已超时和旧轮次的确认会被拒绝。每次等待使用独立的 `user_input_timeout_seconds`；过期或进程中断不会自动恢复或重放操作，已执行的其他操作不会回滚。

自定义工具中的 `context.api.call` 也遵循目标操作的确认规则，必要时会另出一张卡片；自定义工具本身如需确认，可配置工具名或使用 `True`。开发者直接执行的数据库或网络操作属于受信任代码，框架不能拦截这些副作用。

确认接口：`POST /api/v1/agents/sessions/{id}/confirmations/{confirmation_id}`，请求体 `{"approved": true}` 或 `{"approved": false}`。确认 ID 由后端为每次请求生成，不使用模型提供的工具调用 ID。

## 用户填写表单

Agent 内置 `request_input` 工具，无需额外配置。当创建或修改记录缺少信息，或某个字段需要用户决定时，模型可以请求表单：

```python
request_input(
    tool_name="Device_create",
    title="补充设备信息",
    fields=["name", "serial_number"],
    arguments={"body": {"location_id": 3}},
)
```

`tool_name` 必须是当前用户可调用的已注册工具；`fields` 取其 `body` 字段名，没有 `body` 时取根参数名。`arguments` 是已知的工具参数，也可包含所询问字段的预填值。未询问的必填参数必须提供。表单的字段定义、必填约束和权限来自目标工具的 Schema，模型不能提供任意 HTML 或扩大字段权限。

`arguments` 应保留目标工具的完整参数层级：创建使用 `{"body": {"name": "预填值"}}`，更新使用 `{"id": 1, "body": {"name": "预填值"}}`；`fields` 使用 `"name"`，不加 `body.` 前缀。未知值可直接省略，不需要编造占位值。

为兼容模型漏写 `body`，当 `arguments` 中没有 `body` 时，框架会将当前用户可访问且无歧义的请求体字段自动移入 `body`，保留根层路径和查询参数。表单预填、持久化和返回结果均使用归一化后的结构。已有 `body` 时不会合并根层业务字段；未知字段、越权字段、根层与请求体同名的歧义参数仍会被拒绝。校验错误会说明参数路径、缺少的必填字段或失败约束，并提示正确层级，不回显参数值。

前端支持文本、数字、日期、布尔和枚举选择；对象和数组使用 JSON 输入。关联 ID 暂以其原始字段类型输入，不自动查询候选记录。用户提交后，后端校验字段与完整参数并重新检查权限；错误保留在表单中，用户可以修改后重试。成功后卡片显示只读回答摘要，工具返回 `{"tool_name": "Device_create", "arguments": {...}}`，Agent 根据结果继续调用业务工具。

**提交表单只补充信息，不执行或批准目标操作。** 后续业务工具仍遵循 `require_confirmation`。取消表单会向模型返回拒绝结果；停止、过期和重复提交不能继续执行。表单与确认共用持久化记录和等待机制，刷新或 SSE 重连可以继续处理，但服务进程中断后不会自动恢复或重放操作。

统一回答接口为 `POST /api/v1/agents/sessions/{id}/interactions/{interaction_id}`：

- 提交表单：`{"action": "submit", "values": {"name": "设备 A", "serial_number": "SN001"}}`
- 确认操作：`{"action": "approve"}`
- 拒绝请求：`{"action": "reject"}`

原有 `/confirmations/{confirmation_id}` 接口保留兼容。

## 自定义工具

源文件放在 `app/agent_tools/recalculate.py`。首次 sync 会为配置中缺失的工具创建明确抛出 `NotImplementedError` 的骨架；补全业务逻辑后再使用。已有源码不会被覆盖。同步目标是 `generated/backend/app/agent_tools/`。

```python
from pydantic import BaseModel
from app.core.agent_tools import agent_tool


class RecalculateArgs(BaseModel):
    a_id: int


@agent_tool(args_model=RecalculateArgs, roles=["admin", "developer"])
async def recalculate(args, context):
    """读取 A 记录并重新计算统计值。"""
    record = await context.api.call("A", "get", {"id": args.a_id})
    return {"id": record["id"], "result": "请替换为实际计算逻辑"}
```

使用 Pydantic 参数模型、JSON 可序列化结果和 `async def`。`context.api.call` 受同一 Agent 的 `model_tools` 白名单约束，重新校验权限和参数；它是内部 API 辅助方法，不递归触发模型循环的工具 Hook。自定义工具是开发者编写的受信任 Python 代码，其直接数据库操作需自行遵守业务权限。

## 六个 Hook

源文件是 `app/agent_hooks.py`，同步至 `generated/backend/app/agent_hooks.py`。首次配置时生成空函数骨架，之后不覆盖；后续增加 Hook 函数需在源码中定义。每个 Hook 支持一个异步函数，多个处理逻辑在该函数内部组合。

| Hook | event 字段 | 允许返回 |
|---|---|---|
| `before_run` | `messages` | `RunContextOverride(instructions=...)`，追加本轮系统上下文 |
| `before_model` | `messages, step` | `ModelRequestOverride(messages=..., parameters=...)` |
| `before_tool` | `name, arguments, call_id` | `ToolArgumentsOverride(arguments=...)` |
| `after_tool` | `name, arguments, call_id, result, success` | `ToolResultOverride(result=...)` |
| `after_run` | `messages, usage` | `None` |
| `on_error` | `stage, error` | `None` |

所有 Hook 都可以返回 `None` 表示保持不变。`context` 包含 `user`、`session_id`、`run_id`、`api` 和仅本轮共享的 `state`。

```python
from app.core.agent import AgentBlocked, RunContextOverride, ToolResultOverride


async def inject_context(event, context):
    return RunContextOverride(instructions=f"当前用户编号：{context.user.id}")


async def check_operation(event, context):
    if event.name == "A_bulk_delete":
        if len(event.arguments["body"]["ids"]) > 100:
            raise AgentBlocked("单次最多删除 100 条记录")


async def sanitize_result(event, context):
    if event.name == "A_get" and event.success:
        result = dict(event.result)
        result.pop("phone", None)
        return ToolResultOverride(result=result)
```

执行顺序：保存用户消息 → before_run → 循环（before_model → 模型 → 保存模型消息 → 每个工具的校验、before_tool、再校验、执行、after_tool、保存结果）→ after_run。

Hook 得到的是事件数据副本；修改历史不会直接改写数据库。`before_model.parameters` 只接受 `model/temperature/top_p/max_tokens`。修改后的工具参数会重新校验，并在执行前记入审计信息。`before_tool` 抛出 `AgentBlocked` 会向模型返回匹配 `tool_call_id` 的错误结果；其他 Hook 主动阻止时结束本轮。

异常工具执行会触发 `on_error`，随后 `after_tool` 收到 `success=False` 和安全错误信息；实际异常只进服务端日志。Hook 自身异常终止本轮；`on_error` 自身异常只记录日志，不递归调用。`after_tool` 只能修改交给模型的结果，不能撤销已发生的写操作。

## 存储与执行

模型生成在 `generated/backend/app/core/agent_models.py`，随 Agent API 导入并在后端启动时建表，不生成普通 CRUD 接口。

- `agent_session`：`id`（UUID 字符串）、`user_id`（关联现有整数 User.id）、`agent_key`、`title`、`status`、`active_run_id`、`cancel_requested`、`expires_at`、`error`、`created_at`、`updated_at`。
- `agent_message`：`id`（UUID 字符串）、`session_id`、`seq`、`payload`（完整 Chat Completions 消息）、`metadata`（实际执行参数及状态）、`created_at`。SQLModel 属性使用 `details` 映射 SQL 列 `metadata`，避开 SQLAlchemy 保留名称。

历史列表中的删除按钮会删除当前用户的会话及全部消息记录。运行中的会话需先停止；删除不撤销工具已执行的业务操作。后端接口为 `DELETE /api/v1/agents/sessions/{id}`（API 前缀跟随后端配置），成功返回 204。

会话按用户隔离，`(session_id, seq)` 唯一。一次只运行一轮，通过数据库条件更新取得执行权。进程内异步任务执行 Agent；模型以 `stream=True` 增量生成，页面通过带身份认证的 SSE 连接实时更新同一条回复，Markdown 随内容增长渲染。增量文字更新已有消息行，不为每个分片新建消息；断线重连会取得当前完整快照，避免重复追加。停止或异常中断时保留已生成文字并标记中断，未拼接完整的工具调用不会执行。停止请求在当前进程中取消任务，跨进程则在下个执行检查点停止。

进程异常退出后，执行租约过期；读取或继续该会话时将其标记为失败，并为未完成的工具调用补齐“结果未知”的协议消息。不会恢复或重放写操作。已完成数据操作不会因取消或超时回滚。第一版保留并发送完整会话历史，没有自动摘要、分支或压缩。

移除 `agents` 配置后重新 sync 会移除 Agent 页面、API 路由和运行文件，保留开发者源码和数据库已有表。

## 验证

```bash
python -m pytest tests/test_agents.py -q
```

普通测试不调用模型。安装生成后端的依赖和 `openai/jsonschema` 后，额外运行隔离进程中的 SQLite/API 场景，包括权限、消息协议、会话隔离、并发提交和停止执行。未安装这些运行依赖时，该项会明确跳过。

## 对话界面

支持历史搜索、独立会话草稿、Markdown 回复与复制、工具调用和结果合并展开、Enter 发送及 Shift+Enter 换行（兼容中文输入法）。新建对话在第一条消息发送时才创建记录，避免空会话堆积。草稿保留于当前页面内存，刷新页面不会保留未发送内容。

发送后立即展示消息状态，失败保留草稿；连接中断自动重新获取会话，且不会自动重发用户消息。阅读历史时不会强制滚到最底部，可点击“回到最新消息”。窄屏使用历史会话抽屉，支持 Escape 关闭与键盘焦点循环。

## 消息 Markdown

助手回复支持 GFM 表格、任务列表、删除线和嵌套列表。代码块支持语言标识、语法高亮及独立复制，长代码和宽表格在消息内横向滚动。使用 `remark-gfm` 3.x 和 `rehype-highlight` 6.x，与现有 `react-markdown` 8.x 配套。更新后执行 `site sync --install` 安装新增前端依赖。

渲染回归检查：`node tests/support/check_agent_markdown.mjs <包含 node_modules 的临时前端目录>`。该命令会在指定目录生成测试文件，不请求真实模型。
