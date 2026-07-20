# OneSite 培训教程：从 SQLModel 到可运行的管理系统

> 适用对象：会一点 Python、但不一定熟悉 FastAPI 或 React 的开发者。  
> 培训目标：学员能够独立创建一个 OneSite 项目，定义数据模型，生成并运行前后端，并正确使用关联、权限和常见的界面配置。  
> 本文不覆盖 TimescaleDB 相关功能。

## 1. 先建立正确的心智模型

OneSite 是一个**模型驱动的全栈脚手架**。开发者把业务数据结构写成 SQLModel；OneSite 读取这些模型后，自动生成：

| 你维护的内容 | OneSite 生成的内容 |
| --- | --- |
| `models/*.py` 中的 SQLModel | FastAPI 的 Schema、CRUD、Service、REST API |
| 字段类型、默认值、唯一约束 | 数据表、请求校验、表单控件 |
| 外键和中间表 | 关联字段展示、关联选择控件、多选关系 |
| `__onesite__` 和 `site_props` | 菜单、中文文案、搜索、权限、上传组件 |
| `site_config.json` | 环境变量、主题、项目级配置 |

因此，日常开发的主循环是：

```text
定义或修改 models/*.py
        ↓
执行 site sync
        ↓
检查后端 /docs、前端页面和生成代码
        ↓
补充业务代码或继续修改模型
```

### 哪些文件是“源代码”，哪些是“生成物”？

- 优先维护：`models/`、`site_config.json`，以及明确由团队维护的自定义业务代码。
- `backend/app/models/` 是从 `models/` 同步过去的副本，不应作为模型的主编辑位置。
- `backend/app/api/endpoints/`、`schemas/`、`cruds/`、`services/` 与 `frontend/src/pages/` 等会由同步流程生成或刷新。若需长期定制，先确认团队的扩展约定；不要把唯一一份业务规则只写进可能被覆盖的生成文件。

## 2. 环境准备

需要：

- Python 3.10 或更高版本；
- Node.js 与 npm（用于前端）；
- 可选：Docker 或 Podman（用于容器化）。

安装 OneSite：

```bash
pip install onesite
site --help
```

培训环境也可在本仓库根目录以可编辑方式安装：

```bash
python -m pip install -e .
site --help
```

如果 `site` 找不到，先确认安装命令使用的 Python 与当前终端是否一致：

```bash
python -m pip show onesite
python -m onesite.main --help
```

## 3. 第一个项目：库存管理

### 3.1 创建项目并认识目录

在准备存放项目的目录中执行：

```bash
site create inventory-training
cd inventory-training
```

创建后，重点关注：

```text
inventory-training/
├── site_config.json       # 项目级配置
├── models/                # 业务模型：最重要的输入
├── backend/               # FastAPI 应用与生成的后端代码
└── frontend/              # React/Vite 应用与生成的前端代码
```

新项目通常包含 `User`、`SystemConfig`、`CustomConfig` 等基础模型。保留它们；本练习只新增业务模型。

### 3.2 配置项目

编辑 `site_config.json`，先使用 SQLite 以降低培训门槛：

```json
{
  "project_name": "库存管理培训",
  "database_url": "sqlite:///./app.db",
  "upload_dir": "uploads",
  "secret_key": "请替换为培训环境自己的随机值",
  "access_token_expire_minutes": 11520,
  "allowed_origins": [
    "http://localhost:5173",
    "http://localhost:3000"
  ],
  "style": "normal",
  "nav_order": ["category", "product"]
}
```

常用配置说明：

- `database_url`：数据库连接；入门推荐 SQLite。
- `upload_dir`：上传文件的目录。
- `secret_key`：JWT 密钥，真实环境必须使用安全随机值，不能继续使用 `changeme`。
- `allowed_origins`：允许访问 API 的前端地址。
- `style`：内置主题，可用 `normal`、`industrial`、`anime`、`cute`。
- `nav_order`：菜单展示顺序。

### 3.3 新建第一个模型

创建 `models/category.py`：

```python
from typing import Optional
from sqlmodel import Field, SQLModel


class Category(SQLModel, table=True):
    __onesite__ = {
        "translations": {
            "zh": {
                "name": "商品分类",
                "fields": {
                    "name": "分类名称",
                    "description": "说明",
                },
            },
        },
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(
        unique=True,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    description: str = Field(default="")
```

这里已经表达了很多规则：

- `table=True`：该类需要映射为数据库表。
- `id`：主键；通常写成 `Optional[int]`，创建时由数据库生成。
- `unique=True`：名称不可重复。
- `is_search_field=True`：生成列表页的搜索/筛选能力。
- `translations.zh`：让菜单、页面标题和字段标签使用中文。

### 3.4 生成并运行

首次生成和安装依赖：

```bash
site sync --install
```

后续只改模型时通常执行：

```bash
site sync
```

启动全部服务：

```bash
site run
```

也可以分别启动：

```bash
site run --component backend
site run --component frontend
```

默认访问地址：

- 前端：`http://localhost:5173`
- 后端 API 文档：`http://localhost:8000/docs`
- 默认管理员：`admin@example.com` / `admin`

> 注意：当前 CLI 的组件参数是 `--component`；`site run backend` 会被视为项目路径参数，而不是组件名。

### 3.5 首次验收清单

学员应当逐项完成：

- 能登录前端；
- 左侧菜单中出现“商品分类”；
- 能新增、编辑、删除分类；
- 在 `/docs` 中找到分类的 API；
- 尝试创建重名分类，观察唯一性校验。

## 4. 第二步：字段类型、默认值和搜索

创建 `models/product.py`：

```python
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel


class ProductStatus(str, Enum):
    ON_SALE = "on_sale"
    OFF_SHELF = "off_shelf"


class Product(SQLModel, table=True):
    __onesite__ = {
        "translations": {
            "zh": {
                "name": "商品",
                "fields": {
                    "name": "商品名称",
                    "sku": "SKU",
                    "price": "单价",
                    "stock": "库存",
                    "status": "状态",
                    "category_id": "所属分类",
                    "cover_image": "封面图",
                },
            },
        },
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(
        index=True,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    sku: str = Field(
        unique=True,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    price: float = Field(default=0.0)
    stock: int = Field(default=0)
    status: ProductStatus = Field(default=ProductStatus.ON_SALE)
    cover_image: Optional[str] = Field(default=None)
```

重新生成：

```bash
site sync
```

预期效果：字符串、数字、布尔值和枚举会对应到合适的 API 校验和表单控件；名称与 SKU 可用于检索。字段名包含 `image`、`avatar`、`photo` 或以 `_image` 结尾时，会被识别为图片字段；包含 `file`、`attachment` 或以 `_file` 结尾时，会被识别为文件字段。需要明确指定时，也可配置 `component`。

例如强制使用图片组件：

```python
cover_image: Optional[str] = Field(
    default=None,
    sa_column_kwargs={"info": {"site_props": {"component": "image"}}},
)
```

## 5. 第三步：外键与多对多关系

### 5.1 给商品添加分类外键

在 `Product` 中补充：

```python
category_id: Optional[int] = Field(
    default=None,
    foreign_key="category.id",
    sa_column_kwargs={"info": {"site_props": {"reverse_display": True}}},
)
```

再执行 `site sync`。`foreign_key="category.id"` 是关系识别的关键；OneSite 会识别目标表，在表单中提供分类选择，并在列表中尽量展示关联记录的可读标签，而不只是裸 ID。建议把目标模型的名称或编码字段设为 `unique=True` 并标记为 `is_search_field=True`，这样关联项更容易辨认。

### 5.2 多对多：商品标签

创建标签模型 `models/tag.py`：

```python
from typing import Optional
from sqlmodel import Field, SQLModel


class Tag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(
        unique=True,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
```

创建中间表 `models/product_tag_link.py`：

```python
from typing import Optional
from sqlmodel import Field, SQLModel


class ProductTagLink(SQLModel, table=True):
    __onesite__ = {"is_link_table": True}

    product_id: Optional[int] = Field(
        default=None, foreign_key="product.id", primary_key=True
    )
    tag_id: Optional[int] = Field(
        default=None, foreign_key="tag.id", primary_key=True
    )
```

两个外键加上 `is_link_table=True` 表示“纯关系表”。生成器会把它作为商品和标签之间的多对多关系，并在源模型表单中生成多选能力。若中间表增加了非外键业务字段（例如“排序”或“备注”），它不再只是纯关系，也可能需要作为独立 CRUD 页面维护。

## 6. 第四步：权限——先理解，再配置

OneSite 有三个相互独立的层次。权限字符为 `c`（创建）、`r`（读取）、`u`（更新）、`d`（删除）。角色层级为 `developer >= admin >= user`。

| 层次 | 配置位置 | 控制内容 |
| --- | --- | --- |
| 模型权限 | `__onesite__["permissions"]` | API 的 CRUD 权限与页面操作按钮 |
| 字段权限 | 字段 `site_props.permissions` | 字段是否出现在创建、响应、更新 Schema 和表单中 |
| 菜单可见性 | `__onesite__["visible"]` | 哪些角色在导航菜单看到该模型 |

### 6.1 模型级权限

给商品设置：普通用户只读，管理员可增改，开发者可删除：

```python
__onesite__ = {
    "permissions": {
        "user": "r",
        "admin": "cru",
        "developer": "crud",
    },
    "translations": {"zh": {"name": "商品", "fields": {}}},
}
```

未配置 `permissions` 时，默认各角色都有完整 `crud` 权限。字典格式最清晰；当所有角色规则相同，可写字符串，例如 `"permissions": "r"`。

### 6.2 字段级权限

成本价只让管理员以上查看和编辑：

```python
cost_price: float = Field(
    default=0.0,
    sa_column_kwargs={
        "info": {"site_props": {"permissions": "admin-rcu"}}
    },
)
```

也可以逐角色定义：

```python
internal_note: str = Field(
    default="",
    sa_column_kwargs={
        "info": {
            "site_props": {
                "permissions": {"admin": "u", "developer": "rcu"}
            }
        }
    },
)
```

字段级没有 `d`；删除只属于模型级。常见安全实践是：密码哈希字段设置空权限，使其不进入对外 Schema；审计字段如 `created_at` 通常设置为 `"r"`。

### 6.3 菜单可见性并不等于 API 权限

例如财务报表只能由管理员从菜单进入：

```python
__onesite__ = {
    "permissions": {"user": "r", "admin": "crud", "developer": "crud"},
    "visible": ["admin", "developer"],
}
```

这会隐藏普通用户菜单，但普通用户是否还能直接访问 API，取决于 `permissions`，不是 `visible`。培训时应让学员分别用三个角色验证 API 和菜单，避免把“隐藏按钮”误认为“安全控制”。

### 6.4 用户归属数据

当普通用户只能操作自己的记录时，声明所有者字段：

```python
__onesite__ = {"owner_field": "owner_id"}

owner_id: Optional[int] = Field(default=None, foreign_key="user.id")
```

对于非管理员用户，列表会限制为本人数据；创建时所有者会被强制设为当前用户；访问、更新、删除其他人的记录会失败。管理员和开发者可以看到全部记录。

## 7. 常用模型级能力速查

| 需求 | 示例配置 | 说明 |
| --- | --- | --- |
| 中文菜单/字段 | `translations.zh` | 推荐每个对外模型都提供 |
| 搜索字段 | `is_search_field: true` | 写在字段的 `site_props` 中 |
| 单例配置 | `is_singleton: true` | 适合站点设置、业务开关 |
| 隐藏菜单 | `visible: ["admin"]` | 只影响前端导航 |
| 自己的数据 | `owner_field: "owner_id"` | 需有对应用户外键字段 |
| 图片/文件控件 | `component: "image"` / `"file"` | 也支持按字段名自动判断 |
| 前端本地配置 | `frontend_only: true` | 适合浏览器本地偏好 |

单例模型示例：

```python
class StoreConfig(SQLModel, table=True):
    __onesite__ = {
        "is_singleton": True,
        "permissions": {"user": "", "admin": "crud", "developer": "crud"},
        "visible": ["admin", "developer"],
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    store_name: str = Field(default="我的商店")
    low_stock_threshold: int = Field(default=10)
```

## 8. 生成后如何调试与验收

每次 `site sync` 后按下面顺序检查，效率最高：

1. 先看终端是否有模型导入或生成错误。
2. 打开 `http://localhost:8000/docs`：确认路由、请求体字段及权限行为。
3. 打开前端：确认菜单、字段标签、表单、列表和搜索。
4. 用不同角色测试：用户、管理员、开发者的按钮和 API 是否一致。
5. 检查数据库约束：唯一值、必填字段、外键选择。

常见问题：

| 现象 | 优先检查 |
| --- | --- |
| 新模型没有出现在页面 | 是否在项目根目录运行 `site sync`；类是否有 `table=True`；模型文件是否能被导入 |
| 字段没有出现在表单/响应中 | 字段级 `permissions` 是否包含对应的 `c`、`u` 或 `r` |
| 菜单没有显示 | `visible` 配置、模型权限是否给当前角色任何权限、翻译名称 |
| 关联只显示 ID | 外键是否正确；目标模型是否有唯一且可搜索的标签字段 |
| 前端调用 API 失败 | 后端是否运行；`allowed_origins` 是否包含前端地址；查看浏览器网络请求与后端日志 |
| 改模型后页面没变化 | 是否执行了 `site sync`；是否重启了开发服务；是否误改了 `backend/app/models/` 而非 `models/` |

## 9. 容器化（可选进阶）

确认已生成项目并安装 Docker 或 Podman 后：

```bash
site build --component all --engine docker --tag v1 --port 3000
site compose up -d
site compose logs -f
site compose down
```

`site build` 会构建前后端镜像，并生成 `docker-compose.yml`。在真实部署前，必须审查并替换数据库连接、JWT 密钥、跨域来源和镜像标签。

## 10. 建议的半天培训节奏

| 时长 | 内容 | 产出 |
| --- | --- | --- |
| 0–30 分钟 | 概念、安装、创建项目 | 能运行空项目 |
| 30–75 分钟 | 分类与商品模型 | 完成基础 CRUD 与搜索 |
| 75–105 分钟 | 外键与标签多对多 | 完成关联选择与多选 |
| 105–145 分钟 | 角色、字段与菜单权限 | 完成三角色验收 |
| 145–180 分钟 | 上传、单例配置、排错 | 完成一个可演示的库存后台 |

## 11. 课后练习

在库存项目中完成以下功能：

1. 为 `Product` 增加 `low_stock_threshold`，并在低库存商品名称中加入可搜索标识。
2. 新增 `StockRecord`，使用 `owner_field` 让普通用户只能查看自己的盘点记录。
3. 将商品 `cost_price` 设为管理员和开发者可见，普通用户不可见。
4. 新增管理员专用 `StoreConfig` 单例。
5. 使用 `site sync` 后，分别用 API 文档和前端验证三种角色的行为。

完成标准不是“页面看起来正常”，而是模型、API、前端和权限四者行为一致。

## 12. 培训讲师提示

- 让学员先写模型，再运行生成器；不要一开始钻进生成出的 React/FastAPI 文件。
- 每新增一个概念就执行一次 `site sync` 并验收，避免一次积累多处错误。
- 权限练习务必同时验证 API 与前端；前端隐藏不是服务端授权。
- 生产环境的 `secret_key`、数据库密码和跨域名单不能沿用培训示例。
- 需要复杂工作流、跨模型事务或外部系统集成时，把 OneSite 当作高效的基础 CRUD 层，在稳定的自定义扩展点补充业务逻辑。
