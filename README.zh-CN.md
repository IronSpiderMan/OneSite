# OneSite

[English README](README.md) · [完整中文培训教程](docs/onesite-training-guide.md)

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

- 前端：`http://localhost:5173`
- API 文档：`http://localhost:8000/docs`
- 初始管理员：`admin@example.com` / `admin`（上线前必须修改）

日常循环是：修改 `app/models/`、`app/integrations/`、`app/utils/` 或 `site_config.json` → `site sync` → 在 `/docs` 和前端验证。`generated/` 下的内容都是可重新生成的产物，不应作为唯一业务源码。旧项目使用顶层 `models/`、`backend/`、`frontend/` 时仍可继续同步，CLI 不会自动搬迁目录。

## 命令

| 命令 | 作用 |
| --- | --- |
| `site init` | 在当前目录初始化配置、基础模型和图标参考页。 |
| `site create <项目名>` | 创建全栈项目。 |
| `site sync [-i/--install]` | 同步模型并生成代码；`-i` 会安装依赖。 |
| `site run [项目路径] --component backend\|frontend\|all` | 启动后端、前端或两者。 |
| `site build [-c backend\|frontend\|all] [-e docker\|podman] [-t 标签] [-p 端口]` | 构建镜像并生成 `deploy/docker-compose.yml`。 |
| `site build --component desktop` | 为当前 macOS 或 Windows 平台构建原生 Tauri 客户端。 |
| `site compose [--engine docker\|podman] up -d` | 使用 `deploy/docker-compose.yml` 执行 Compose；也支持 `down`、`logs -f`。 |

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

`site_config.json` 常用配置包括 `project_name`、`database_url`、`upload_dir`、`secret_key`、`allowed_origins`、`style`、`radius`、`nav_order`。`extra` 下的所有键值都会同步到后端 `.env`；可通过 `"extra": {"TIMEZONE": "Asia/Shanghai"}` 设置系统时区。它默认使用上海时区，并控制前端默认时间显示与 APScheduler 的 cron 调度；写入数据库的 datetime 会统一转换为 UTC。内置结构主题：`normal`、`industrial`、`anime`、`cute`、`emqx`、`neuron`。`style` 是构建时主题，执行 `site sync` 时会选择对应主题目录下的列表、详情、创建、仪表盘、设置、个人资料、单例页和 CSS 模板；缺少覆盖模板时回退到公共模板。`normal` 通过生成的兼容适配层使用 Ant Design 6，并且只有 normal 构建会增加 `antd` 依赖；明暗模式会同步到 Ant Design 的主题算法。生产环境务必更换 `secret_key`、数据库地址和跨域来源。

模型级选项写入 `__onesite__`：

- `translations`、`icon`：中英文文案和菜单图标。
- `permissions`、`visible`：接口 CRUD 权限和菜单可见性。
- `owner_field`：用户只能访问自己拥有的数据。
- `is_link_table`、`is_singleton`、`frontend_only`、`page_edit`：关系、单例、纯前端和编辑页行为。
- `actions`、`importable`、`exportable`、`import_key`：自定义操作与 CSV 导入导出。
- `refresh_interval`、`visualize`：自动刷新及统计图表。
- `is_notification_table`、`time_series_table`：通知/WebSocket 与时序表配置。

权限分三层：模型级 `c/r/u/d`，字段级 `c/r/u`，以及 `visible` 菜单可见性。角色由低到高为 `user`、`admin`、`developer`。字段权限未配置时会继承模型权限（移除 `d`）；默认 `id` 隐藏、`created_at` 只读、`updated_at` 可读写。用字段 `site_props.permissions` 显式配置即可覆盖默认值。

字段 `site_props` 还支持 `is_search_field`、`component`（`image`/`images`/`file`/`textarea`/`json`/`location`）、`create_optional`、`update_optional`、`reverse_display`、`allow_download`、`group`、`fixed_keys`、`lock_keys` 等。

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

## MQTT 回调

MQTT Broker 参数和 Topic 绑定继续写在 `site_config.json`：

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

旧布局项目仍可使用顶层 `utils/`，它会同步到 `backend/app/utils/`。

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
先在 `site_config.json` 中配置桌面客户端访问的 FastAPI 地址：

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

`site build` 会生成 `deploy/docker-compose.yml`；`site create`、`site init` 和 `site sync` 会确保 `deploy/.env.example` 存在。部署时可复制为 `deploy/.env` 并填写环境差异，`site compose` 会自动加载它。若 `database_url` 以 `postgresql` 开头，会加入 PostgreSQL 服务。旧项目在没有 `deploy/docker-compose.yml` 时仍可使用根目录 Compose。新项目的开发源码位于 `app/models/` 和 `app/integrations/`；可重新生成的后端、前端与各自的 Dockerfile 位于 `generated/backend/` 和 `generated/frontend/`。

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
├── site_config.json
└── icon-reference.html
```

更多逐步示例请阅读 [完整中文培训教程](docs/onesite-training-guide.md)，并参考 `examples/`。
