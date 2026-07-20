# OneSite

[English README](README.md) · [完整中文培训教程](docs/onesite-training-guide.md)

OneSite 是一个模型驱动的全栈代码生成 CLI。开发者维护 `models/` 中的 SQLModel；执行 `site sync` 后，自动生成 FastAPI 的 Schema、CRUD、Service、REST API，以及 React/Vite 的页面、服务、菜单、国际化和主题资源。

## 安装与快速开始

要求 Python 3.10+；生成前端还需要 Node.js/npm；容器部署可选 Docker 或 Podman。

```bash
pip install onesite
site create inventory
cd inventory

# 在 models/ 中定义或修改 SQLModel
site sync --install
site run
```

- 前端：`http://localhost:5173`
- API 文档：`http://localhost:8000/docs`
- 初始管理员：`admin@example.com` / `admin`（上线前必须修改）

日常循环是：修改 `models/*.py` 或 `site_config.json` → `site sync` → 在 `/docs` 和前端验证。`backend/app/models/` 是同步副本；生成的 Schema、接口、CRUD/Service 与前端页面可能在同步时覆盖，不应作为唯一业务源码。

## 命令

| 命令 | 作用 |
| --- | --- |
| `site init` | 在当前目录初始化配置、基础模型和图标参考页。 |
| `site create <项目名>` | 创建全栈项目。 |
| `site sync [-i/--install]` | 同步模型并生成代码；`-i` 会安装依赖。 |
| `site run [项目路径] --component backend\|frontend\|all` | 启动后端、前端或两者。 |
| `site build [-c backend\|frontend\|all] [-e docker\|podman] [-t 标签] [-p 端口]` | 构建镜像并生成 Compose 文件。 |
| `site compose [--engine docker\|podman] up -d` | 执行 Compose 命令；也支持 `down`、`logs -f`。 |

`backend`/`frontend` 是 `--component` 选项值，正确写法是 `site run --component backend`，不是 `site run backend`。

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

## 配置与权限

`site_config.json` 常用配置包括 `project_name`、`database_url`、`upload_dir`、`secret_key`、`allowed_origins`、`style`、`radius`、`nav_order`。内置主题：`normal`、`industrial`、`anime`、`cute`。生产环境务必更换 `secret_key`、数据库地址和跨域来源。

模型级选项写入 `__onesite__`：

- `translations`、`icon`：中英文文案和菜单图标。
- `permissions`、`visible`：接口 CRUD 权限和菜单可见性。
- `owner_field`：用户只能访问自己拥有的数据。
- `is_link_table`、`is_singleton`、`frontend_only`、`page_edit`：关系、单例、纯前端和编辑页行为。
- `actions`、`importable`、`exportable`、`import_key`：自定义操作与 CSV 导入导出。
- `refresh_interval`、`visualize`：自动刷新及统计图表。
- `is_notification_table`、`time_series_table`：通知/WebSocket 与时序表配置。

权限分三层：模型级 `c/r/u/d`，字段级 `c/r/u`，以及 `visible` 菜单可见性。角色由低到高为 `user`、`admin`、`developer`。字段权限未配置时会继承模型权限（移除 `d`）；默认 `id` 隐藏、`created_at` 只读、`updated_at` 可读写。用字段 `site_props.permissions` 显式配置即可覆盖默认值。

字段 `site_props` 还支持 `is_search_field`、`component`（`image`/`file`/`textarea`/`json`）、`create_optional`、`update_optional`、`reverse_display`、`allow_download`、`group`、`fixed_keys`、`lock_keys` 等。

## 已生成能力

- JWT 登录、角色权限、所有者隔离
- CRUD、唯一性校验、列表检索与筛选
- 图片/文件上传、JSON 与嵌套 Pydantic 编辑器
- 外键标签、多对多、树结构、单例配置页
- 自定义按钮、CSV 导入导出、通知中心和 WebSocket
- 自动刷新、统计图表、APScheduler 定时任务
- EN/ZH 国际化、四套主题
- Docker/Podman、Compose 与可选 TimescaleDB 时序能力

## 部署与目录

```bash
site build --engine docker --tag v1 --port 3000
site compose up -d
site compose logs -f
```

`site build` 会生成 `docker-compose.yml`；若 `database_url` 以 `postgresql` 开头，会加入 PostgreSQL 服务。项目的核心目录是 `models/`（源码）、`backend/app/api/endpoints/`、`schemas/`、`cruds/`、`services/`（生成后端）和 `frontend/src/pages/`、`services/`、`stores/`（生成前端）。

更多逐步示例请阅读 [完整中文培训教程](docs/onesite-training-guide.md)，并参考 `examples/`。
