# 数据库迁移与本次生成器变更

## Alembic 工作流

在项目根目录使用 `site db`。迁移采用后端相同的数据库配置，CLI 使用当前 Python 环境，因此该环境需要安装生成后端的 `requirements.txt`（包括所选数据库驱动及 Alembic）。

空数据库：

```bash
site db revision -m "initial schema"
# 检查 app/migrations/versions/ 中的 upgrade 和 downgrade
site db upgrade
site run
```

已通过旧版 `create_all` 建表的数据库：保持与现有数据库匹配的旧模型，先执行：

```bash
site db baseline -m "adopt existing schema"
```

基线会检查现有数据库与模型是否一致；不一致时拒绝接管。成功后生成可重建空库的初始迁移，并为现有数据库记录版本，不删除现有业务数据。不要在修改模型以后才为旧结构建立基线。

后续修改 `app/models/` 后：

```bash
site db revision -m "add entry note"
# 检查生成的迁移，按需补充数据回填或改名操作
site db upgrade
site db current
site db check
```

`revision` 和 `baseline` 会在执行前后同步代码。其他命令使用当前生成结果；手动修改迁移文件后，执行 `site sync` 将历史同步到部署目录。

| 命令 | 用途 |
| --- | --- |
| `site db revision -m "message"` | 自动比较数据库与模型，生成候选迁移，不执行变更 |
| `site db baseline` | 为结构与模型一致的既有数据库建立初始版本 |
| `site db upgrade [revision]` | 升级，默认 `head` |
| `site db downgrade <revision>` | 回退到明确版本；`-1` 表示回退一步 |
| `site db current` | 查看当前数据库版本 |
| `site db history` | 查看迁移历史 |
| `site db check` | 检查当前模型是否还有未记录的结构差异 |
| `site db stamp <revision>` | 仅记录版本，不执行 DDL；用于人工核对后的版本修复 |

Alembic 自动生成的是待检查的迁移。列/表改名、数据回填、数据库专有对象等仍需手工编辑，回退也取决于对应 `downgrade()` 的实现。SQLite 使用 batch migration 支持表结构调整。参考 [Alembic 自动生成说明](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)。

## 历史归属与部署

- `app/migrations/` 是开发者维护的源文件，应提交到版本控制；`site sync` 保留迁移历史和自定义 `env.py`。
- `generated/backend/migrations/` 是部署副本，配套 `alembic.ini`。
- 已有迁移历史时，后端启动检查数据库版本，未升级会明确报错，启动不自动执行升级。
- 没有迁移历史的项目暂时保留 `create_all` 兼容行为；需要管理结构演进时，应建立初始迁移或基线。
- 独立部署时可在生成的后端目录运行 `python -m app.core.migrations upgrade`。使用与应用相同的数据库环境变量，在启动应用前执行一次。
- Nuitka 生产镜像附带迁移配置和历史，但不提供 Python 迁移运行器；使用安装后端依赖的 Python 环境或开发镜像执行迁移，再启动生产应用。不要让每个应用 worker 同时执行升级。
- 当前回归测试覆盖 SQLite 的真实升级、保留数据、回退和旧库接管；PostgreSQL/TimescaleDB 的特有 DDL 需要在对应部署环境验证。

## 权限与生成行为

模型权限字典按当前角色精确匹配；`admin`、`developer` 不再因为角色级别高而继承未配置的操作。旧字符串配置仍在解析阶段展开为兼容的权限字典。

字段的 `c/r/u` 在后端分别控制提交与响应序列化：主动提交无权写入的字段返回 403，无权读取的字段从响应移除。前端表单保存同步过滤不可写字段。`/me` 仍保留自己的入口规则，同时执行字段权限检查。

归属限制覆盖联合键详情和关联列表。关联列表在分页与计数前过滤目标记录，同时校验源记录归属与目标模型读取权限。普通外键展示标签同样受目标读取与字段权限限制。无效的 `owner_field` 配置会导致同步失败。

上传接口要求有效登录，`/uploads` 文件访问保持公开。

生成资源统一按模型类名转换为 snake_case，例如 `OrderItem` 对应 `order_item.py` 与 `/order_items/`；源码文件可以包含多个模型，移动或改名源码文件不改变资源名。**升级时，原来文件名与类名不一致的模型，其旧 API 路径会改变；调用方需要同步更新。** 菜单 `NavModel(model=...)` 同时兼容能唯一对应模型的旧源码模块名（如 `dgroup` → `d_group`）；同一模块包含多个候选模型时，必须使用模型资源名。重复资源名及与内置 API 冲突的名字会在发布前报错。

`site sync` 在临时目录完成生成及 Python 语法检查，再发布结果；渲染失败不改动原产物，发布异常会恢复已修改文件。清单记录生成器管理的文件，删除模型后清理陈旧代码；数据库、上传文件和已安装依赖保留。首次接管旧项目只清理已知生成代码目录。同步期间的并发运行由 `.onesite-sync.lock` 阻止；进程被强制终止后，确认没有同步进程再清理残留锁。发布是逐文件替换与回滚，不能替代生产部署的进程切换。
