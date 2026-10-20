**OneSite 项目设计审查 · 2026-09-06**

当前最值得优先解决的是权限语义统一、生成产物生命周期和持久化状态管理。CLI → 分阶段生成 → 模板的主线已经清晰，`app/` 与 `generated/` 分离、主题覆盖公共模板、独立运行的生成后端也值得保留。问题主要出在这些机制组合后的边界，而不是缺少功能。

本次未修改实现代码。审查基于当前工作区，包括尚未纳入 Git 的测试与文档。覆盖 CLI、配置、模型内省、关系解析、生成与资源同步、主要后端/前端模板、鉴权、任务运行时、构建配置及测试。没有启动真实 PostgreSQL/TimescaleDB、消息中间件、桌面应用或进行完整浏览器端到端测试，因此不把这份审查等同于所有功能已验收。

**验证结果**

- `.venv/bin/python -m pytest -q`：435 passed、2 skipped、22 warnings，28.43 秒；测试目录有 74 个 `test_*.py` 文件。
- `.venv/bin/python -m ruff check src tests`：通过。模板文件本身不等于被这项 Python 检查覆盖。
- 在 `/tmp/onesite-design-audit/` 创建独立项目，复现生成覆盖、权限判断、字段输出、owner 查询差异、删除后残留、失败同步副作用、配置转义及依赖覆盖。
- 临时项目采用 industrial 主题；借用已有示例的 `node_modules`，执行 `tsc --noEmit` 通过。没有重新安装依赖，此结果只覆盖该样例和现有依赖组合。
- 权限行为验证执行了从实际生成文件提取的原函数/方法；数据归属验证使用受控的 service 返回值，未启动完整 HTTP 应用。当前仓库虚拟环境缺少 httpx、python-jose 等生成后端运行依赖，故不能声称已完成真实 HTTP/数据库端到端验证。

以下 P1 表示应优先修复的访问控制或核心正确性问题；P2 表示应纳入近期稳定性建设的问题。每项区分直接复现与代码审查结论。

**1. P1：逐角色独立授权，被编译成了角色等级阈值【已复现】**

配置中的权限字典允许各角色独立授权，但 `_resolve_min_roles()` 取“第一个拥有权限的角色”，`require_role()` 再允许这个等级及以上的所有角色。没有任何角色拥有权限时，默认值仍是 DEVELOPER。

复现：配置 `user=crud, admin=r, developer=r`，ADMIN 仍通过创建鉴权；所有角色只有 `r` 时，DEVELOPER 仍通过删除鉴权。普通 API 模板仍生成这些写端点。另一方面，整个 router 依赖读取权限，使“只能创建、不能读取”的角色可能无法创建。导入/导出又按权限字典精确检查，于是同一模型出现两种规则。

建议：将权限字典编译成统一的 `can(role, operation)` 策略，端点逐操作校验；全角色无权限就不生成端点或明确拒绝。router 只负责认证，避免把读取权限附加到所有写入操作。如果产品希望 developer 永远拥有特权，应明确写入配置契约，并让前后端一致遵循。

证据：[角色计算](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/codegen/phases/relationships.py:131)、[等级鉴权](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/backend/app/core/deps.py:53)、[router 读取门槛](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/codegen/api.py.j2:69)。

**2. P1：字段权限没有成为普通 CRUD 的后端约束【已复现读响应及输入 Schema】**

字段 `role_permissions` 被合并为所有角色权限的并集 `field.permissions`，用于生成通用 Create、Update、Read Schema。普通 `to_read()` 直接验证完整数据，没有按当前角色过滤；普通写入链路也没有统一字段授权。

复现：`secret` 对 user 的权限为 `""`，对 admin/developer 为 `cru`。以 user 身份调用生成的 `to_read()`，返回值仍包含 `secret`；`ProbeUpdate(secret="changed")` 也接受这个字段。该输入测试不单独证明数据库已被写入，但模板中的普通 service 没有角色过滤。内置 `UserUpdateMe` 对额外可更新字段同样使用权限并集，值得一起修复。

建议：统一传递用户上下文；写入前校验提交字段白名单，读取时进行角色相关的序列化。不要只删除必填字段后继续套用同一个 Read Schema，否则会变成响应验证错误。列表、详情、关联结果、导出、自助资料更新、extra/override 字段都应遵循同一规则。

证据：[权限并集](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/codegen/introspect.py:892)、[Schema](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/codegen/schema.py.j2:152)、[读响应](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/codegen/service.py.j2:119)、[自助资料 Schema](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/codegen/user_schema.py.j2:67)。

**3. P1：数据归属限制依赖具体端点，联合键和关联查询存在缺口【联合键已复现；关联查询为静态结论】**

普通 `/{id}` 会检查 owner；`/by_<union_key>` 没有对应检查。在未配置 read resolver 时，联合键端点甚至不接收当前用户。复现使用合法的 `owner_id → user.id` 外键和两个联合键字段：访问 owner=2 的记录，用户 1 的普通详情返回 404，同样的数据通过联合键函数返回。

M2M/reverse-M2M 的端点与 service 直接按父 ID 查关联，未统一检查父对象归属、目标模型读取权限或目标对象归属。这个静态发现未做数据库关系样例端到端验证。

建议：建立 `AccessContext` 和统一的 scoped query，把 owner 条件放进查询入口；关系查询同时验证源对象和目标模型策略。不要在每种端点里重复拼权限分支。

证据：[联合键端点](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/codegen/api.py.j2:614)、[普通详情 owner 检查](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/codegen/api.py.j2:705)、[关联接口](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/codegen/api.py.j2:1176)、[关联 service](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/codegen/service.py.j2:639)。

**4. P1：文件存储绕过了业务权限体系【静态确认】**

生成的 `/upload` 没有认证依赖，router 挂载也没有补充认证；应用层没有文件大小上限、类型白名单和用户配额，异步端点内使用同步文件复制。`/uploads` 整个目录通过 StaticFiles 公开提供，工具和定时任务的输出也放在该目录。

这意味着默认应用允许匿名上传，并且知道任务产物 URL 的人可以绕过任务列表权限下载文件。随机任务 ID 不等于权限控制。实际上传大小可能另受反向代理限制，不能据此称所有部署都无限上传。

建议：普通上传默认认证并限额；公开媒体与私有文件分目录；私有产物通过校验执行记录归属的下载接口提供。明确允许公开的图片再使用静态 URL。

证据：[上传端点](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/codegen/backend_api_upload.py.j2:8)、[router 挂载](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/codegen/router.py:24)、[公开目录](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/codegen/backend_main.py.j2:237)、[工具产物路径](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/codegen/tool_runtime.py.j2:88)。

**5. P1：生产默认凭据与开发便利混在一起【静态确认】**

默认 JWT 密钥为 `changeme`；默认初始账号为 `admin@example.com`、密码 `admin`，初始化将其设为 DEVELOPER。未配置部署差异时，这些值会进入生成配置和环境文件。README 提醒修改密钥，但运行时未强制校验。

建议：创建项目时生成随机密钥，生产启动拒绝占位密钥；初始化管理员采用显式凭据或一次性初始化流程。生产模式不要自动保留通用开发账号。配置里声明的密钥会被写进生成代码，生产秘密应从运行环境注入，避免成为代码/镜像中的默认值。

证据：[SiteConfig 默认值](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/config.py:665)、[环境默认值](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/codegen/envsync.py:27)、[初始 developer](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/backend/app/initial_data.py:22)。

**6. P1：模型身份与 Python 文件名耦合，会静默覆盖输出【已复现】**

内省支持从一个模块收集多个 SQLModel，但给这些模型相同的 `module_name`；Schema、CRUD、API、前端页面等又以此命名。一个 `probe.py` 中放置三个表模型，生成器成功结束，最后只剩最后一个模型的后端实现，聚合 router 三次注册同一个 `/probes`。

建议：分离 `model_key`、`source_module`、`table_name`、`route_name`、`output_path`；生成前统一检查所有产物路径和路由冲突。即使暂时要求“一文件一个表模型”，也必须显式报错，而不是成功覆盖。内省对导入进来的模型类也没有来源去重，应纳入身份解析规则。

证据：[内省收集](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/codegen/phases/introspect_models.py:932)、[身份组装](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/codegen/phases/introspect_models.py:868)、[输出命名](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/codegen/phases/generate.py:333)。

**7. P2：生成过程边校验边覆盖，失败后项目处于混合版本【已复现】**

Phase 1 已覆盖 `.env`，之后同步模型，再进行内省、关系解析、渲染。配置或模型在后续阶段报错，不会恢复前面的写入。

复现：修改项目名称并加入有语法错误的模型，`sync` 抛出 `ModelIntrospectionError`，但现有 `.env` 已改变，生成目录中已留下无法导入的模型文件。

建议：先解析/校验/编译生成计划，再在 staging 目录渲染；完成 Python 编译、路径冲突检查和适当的前端验证后统一应用。为同步增加 `--check`/`--dry-run`、变更清单及失败恢复。开发者源码脚手架也应属于明确的生成计划。

证据：[pipeline 顺序](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/codegen/pipeline.py:39)、[提前同步环境](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/codegen/phases/config.py:91)、[直接写入](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/codegen/file_utils.py:16)。

**8. P2：删除模型只清理模型镜像，其他生成产物没有统一回收【已复现】**

删除 `app/models/read_only_probe.py` 后同步：后端 model 文件消失，但旧 Schema、CRUD、API 文件、生成测试和前端页面仍然存在。旧 Schema 仍引用已经删除的 model。新 router 不再挂载旧接口，所以不能据此断言旧 API 仍对外开放；确定的问题是增量输出不等于干净生成，旧文件可能导致后续收集、构建或人工维护失败。

建议：维护生成产物 manifest，记录每个产物的所属模型/功能、模板和内容 hash；同步成功时只删除上次由生成器管理、这次已不需要的文件。需要验证“增量同步结果等于同源干净生成结果”，而不仅是“再次同步能运行”。

证据：[仅模型镜像回收](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/codegen/phases/sync_models.py:66)、[零散页面回收](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/codegen/phases/generate.py:405)。

**9. P2：模型驱动代码更新，数据库却缺少统一的版本迁移机制【静态确认】**

初始化调用 `SQLModel.metadata.create_all`，可以创建缺失的表，但不会把已有业务表迁移到新的字段、类型或约束。模板已为 operation_log 外键和后台任务时间列加入专门 ALTER 逻辑，说明项目自身已经遇到这个需求，目前处理方式仍是按功能打补丁。

建议：提供受版本管理的数据库迁移目录、schema diff 和显式升级命令，可结合 Alembic；生成代码与应用迁移分开执行。自动化适合创建候选迁移，删除/重命名/类型变更要有明确的数据迁移逻辑。SQLite 与 PostgreSQL 分别验证外键、索引、约束和升级路径。

证据：[建表与特殊升级](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/codegen/db.py.j2:79)。

**10. P2：配置强类型化不彻底，生成代码缺少统一字面量编码【已复现】**

`SiteConfig` 默认允许额外字段，JSON 配置则直接返回普通 dict，再由多个 validator 和 `setdefault` 分散处理。`SiteConfig(secret_keey="...")` 不报错，真正的 `secret_key` 仍为 `changeme`。这会让拼写错误变成静默默认行为。新配置中的 PublicDashboard 等结构在 Pydantic 与字典 validator 中还有重复规则。

模板直接把 `project_name`、密钥、数据库 URL 等插入 Python 双引号字符串。复现：合法名称 `A "quoted" title` 会令生成的配置第 7 行出现 SyntaxError。Python 字面量和 JSON 字面量也不应混用。

建议：Python/JSON 入口都先转成同一个严格、规范化的配置模型；兼容旧键通过显式迁移适配器处理。模板提供 `py_literal`、`ts_literal` 等目标语言编码函数，逐步对完整上下文启用 StrictUndefined。严格字段校验和语义校验应在写文件前结束。

证据：[允许 extra](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/config.py:22)、[JSON 直接返回](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/codegen/config.py:850)、[未转义字符串](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/codegen/backend_config.py.j2:7)、[Jinja 环境](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/codegen/render.py:32)。

**11. P2：后台任务状态持久化了，但执行所有权仍属于单进程【静态确认，多实例推断未实测】**

队列是进程内无界 `asyncio.Queue`，只有一个消费循环逐项 await。每个 Web 进程的 lifespan 都启动 scheduler 和恢复逻辑；工具恢复逻辑把数据库里所有 queued/running 记录标为失败，未限定所属 worker 或 lease。

在多个实例共享数据库或滚动重启时，新实例可能把其他实例正在执行的任务标为失败；定时任务也缺少统一调度所有权。单进程中，一个长任务会阻塞这个队列后面的其他任务。不能仅凭存在 RabbitMQ/Redis 配置就认为任务已分布式化。

建议：近期明确支持的 worker 数量并加入保护；随后从 Web 进程拆出调度器和 worker，使用持久化领取、worker_id/lease/heartbeat、幂等执行和限流并发。已有任务执行表可以保留作为状态接口。

证据：[队列执行](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/codegen/task_queue.py.j2:37)、[启动流程](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/codegen/backend_main.py.j2:112)、[全局失败恢复](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/codegen/tool_runtime.py.j2:103)、[定时任务恢复](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/codegen/scheduled_task_runtime.py.j2:151)。

**12. P2：后端扩展源码有归属，扩展依赖没有对应的声明机制【覆盖已复现】**

项目允许开发者维护自定义后端模块、工具和任务，但每次同步都会用模板覆盖生成后端 requirements，再追加 MQTT/Kafka 的已知依赖。手动加入一条自定义依赖后再同步，该条目消失。当前 SiteConfig 没有相应通用后端依赖字段；前端 custom feature 已有 dependencies/dev_dependencies，前后端扩展体验不一致。

大部分后端依赖未限定兼容范围，仓库自身的 uv.lock 并不能锁定生成项目的 requirements。相同模型在不同时间安装可能得到不同运行环境。

建议：增加开发者持有的 backend requirements/pyproject 或配置依赖字段，与生成器基础依赖合并并检测冲突；同时生成项目级 lock。对生成器、生成后端、前端主题和可选集成分别维护兼容性矩阵。

证据：[requirements 覆盖](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/codegen/assets.py:816)、[只追加集成依赖](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/codegen/assets.py:24)、[后端依赖模板](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/backend/requirements.txt:1)。

**13. P2：测试能证明生成器运行，但生成项目自身的测试模板已偏离实际应用【静态确认】**

当前 435 项测试是有价值的回归基础，但存在大量文本断言，不能覆盖权限组合的真实行为。生成的 backend_test 模板本身有明确问题：请求路径缺 `/api/v1`；创建测试用户仍设置 is_superuser 而不设置 role；db_session fixture 未被 client/测试依赖且非 autouse；使用 SQLAlchemy AsyncSession，但生成 CRUD 使用 SQLModel 的 `session.exec()`。单例测试接受 404，还可能将错误路径误判为通过。datetime 样例分支直接生成 Python 中未定义的 `null`。

建议：保留元数据/渲染单测，增加真正可启动的最小生成项目测试。修复公共 conftest，隔离数据库和 dependency_overrides，使用正确 session；对三个角色、CRU 字段、owner、联合键、M2M、导出、/me 建立授权矩阵。CI 应运行干净生成、增量变更、后端行为测试，以及至少代表性主题的 tsc/build。当前工作区未见 `.github` CI 配置，不能据此排除仓库外部的 CI。

证据：[测试模板](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/codegen/backend_test.py.j2:15)、[实际 API 前缀](/Users/zackfair/Workplace/PythonWorkplace/OneSiteTool/src/onesite/templates/codegen/backend_main.py.j2:239)。

**架构优化方向与实施顺序**

| 顺序 | 工作 | 验收依据 |
| --- | --- | --- |
| 1 | 统一操作、字段、owner 策略；修复文件访问和生产默认凭据 | 权限矩阵中禁止的操作/字段在所有入口均被拒绝或过滤 |
| 2 | 稳定模型身份、冲突检查、生成计划、manifest 和 staging | 同源干净生成与增量生成一致；失败不改变可运行版本 |
| 3 | 统一配置与目标语言字面量编码，补齐依赖来源及迁移 | 错误配置在落盘前失败；生成项目可锁定、安装并升级 |
| 4 | 修复生成项目测试，建立组合用例和自动检查 | HTTP/数据库行为、tsc/build、增量生成均有可重复验证 |
| 5 | 根据实际部署需求拆分 scheduler/worker | 多实例下执行所有权明确、重启恢复不干扰其他实例 |
| 6 | 拆分大模板与配置中间表示，做性能优化 | 修改一个功能不需要在多个入口复制规则；生成与运行性能有基线 |

其中测试不是最后才开始，应随前面每项修复增加回归用例。

目前 `pipeline.py` 只有 118 行，但复杂度仍集中在 `generate.py`（1646 行）、`introspect.py`（1924 行）、`relationships.py`（1426 行），以及详情页（3374 行）、列表页（2648 行）、service（1692 行）、CRUD（1500 行）、API（1440 行）的模板中。优化应按权限、查询、表单、关系编辑、导入导出等职责提取共同组件；只移动文件不会减少分支组合。

可以建立明确的中间表示：RawConfig → ValidatedConfig → ModelIR → ResolvedIR → ArtifactPlan。当前 ModelDefinition 仍是动态 dict，阶段之间隐式补字段；更严格的 IR 能让漏字段与不支持的组合提前失败。现有主题覆盖公共模板的机制可以继续保留。

性能方面，优先限制普通列表/关联接口中的无界 `size=-1`、把大批量导出转为分页流式任务，并为任务队列加入有界并发。生成端每次写文件都重新创建 Jinja Environment，可按主题复用一次生成中的环境与模板缓存；先测量耗时再决定是否需要更复杂的增量编译。

文档也需跟随实现：当前 README 已采用 `app/`、`generated/` 与 `site_config.py`，但 AGENTS.md 仍描述顶层 models/backend/frontend 和旧 `site run` 用法，部分 examples 也保留旧布局。应统一维护文档，并把支持的示例作为冒烟用例。本次 435 项通过包含当前未跟踪的 tests；发布前需要确保所依赖的测试和文档进入版本控制。

**本次复现材料**

临时材料位于 [/tmp/onesite-design-audit](/tmp/onesite-design-audit)：`generate_probe.py` 建立多模型覆盖样例，`split_probe.py`、`update_probe.py` 分离模型并设置有效 owner/联合键，`runtime_probe.py` 执行权限函数验证，`lifecycle_probe.py` 验证删除、失败同步和配置转义，`dependency_probe.py` 验证依赖覆盖。生成日志也在该目录。脚本按上述顺序使用；首次创建脚本需要目标项目目录尚不存在。`/tmp` 不是长期保存位置，核心结论及来源已经记录在本文。
