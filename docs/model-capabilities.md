# 模型能力

在 SQLModel 的 `__onesite__` 中声明 `capabilities`，运行 `site sync --install` 生成界面和后端操作。一个模型可以声明多种能力，每个 `kind` 最多声明一次。生成器会验证字段是否存在、类型是否匹配，并沿用模型原有的记录 ID。

```python
from onesite.config import CapabilityConfig, CapabilityKind, OneSiteConfig
from sqlmodel import Field, SQLModel


class Gateway(SQLModel, table=True):
    __onesite__ = OneSiteConfig(
        capabilities=[CapabilityConfig(
            kind=CapabilityKind.OPCUA_SERVER,
            field_map={"endpoint": "server_url", "password": "credential"},
            permissions={"browse": ["admin", "developer"]},
        )],
    )

    id: int | None = Field(default=None, primary_key=True)
    name: str
    server_url: str
    username: str | None = None
    credential: str | None = None
```

`field_map` 的键是能力规定的字段名，值是模型实际的字段名。省略的项按同名映射。也可以使用字典配置，例如 `__onesite__ = {"capabilities": [{"kind": "mqtt_broker"}]}`。

| `CapabilityKind` | 必需字段 | 操作 |
| --- | --- | --- |
| `OPCUA_SERVER` | `endpoint: str`，`username` 和 `password` 为 `str` 或 `str \| None` | `browse` 在详情页展开 OPC UA 地址空间 |
| `MQTT_BROKER` | `endpoint: str`，`username` 和 `password` 为 `str` 或 `str \| None` | `subscribe` 打开记录的订阅页面，查看匹配 topic filter 的实时消息和保留消息 |
| `DATABASE` | `host: str`、`port: int`、`username: str`、`password: str`、`database: str`、`driver: Enum` | `list_tables` 查看可读的表和列结构，`read_rows` 分页预览数据，`query` 选择列、筛选和排序 |

OPC UA 使用 `opc.tcp://`，端口默认 4840。证书认证相关设置可通过可选字段 `auth_type`、`security_policy`、`security_mode`、`app_uri`、`cert_path`、`key_path`、`server_cert_path`、`request_timeout_seconds` 提供。节点浏览与原有 OPC UA 插件可以在不同模型上同时使用。

MQTT 订阅页使用 MQTT 5。Endpoint 可用 `mqtt://` 或 `mqtts://`，默认端口分别是 1883 和 8883。离开页面会释放订阅。页面的 topic 列表来自当前会话收到的消息，订阅权限由 Broker 的账号和 ACL 控制。

数据库 `driver` 目前支持 `postgresql`。在项目模型文件中定义枚举，例如 `class DatabaseDriver(str, Enum): POSTGRESQL = "postgresql"`。浏览器使用配置的数据库账号读取普通表和分区表。为该账号授予所需 schema 的 `USAGE` 和表的 `SELECT`。查询表单使用结构化条件，在只读事务中执行。

每个操作都检查模型读取权限、记录归属和能力操作授权。能力操作默认允许 `admin`、`developer`，用 `permissions` 可逐项覆盖，空列表禁用该项。创建能力模型记录和修改连接字段由 `admin`、`developer` 执行，仍受模型和字段权限约束。

映射后的密码字段只写。保存非空密码前，为后端设置稳定的 `CAPABILITY_SECRET_KEY`（至少 32 个字符），或者使用符合长度要求的 `SECRET_KEY`。本地可以通过环境变量或 `generated/backend/.env` 设置，Compose 部署可在 `deploy/.env` 设置 `CAPABILITY_SECRET_KEY`。加密后的值保存在模型原有字段中，字段需能容纳密文。给已有模型添加能力时，重新保存已有密码即可加密。更新表单中留空会保留已保存的密码，OPC UA 和 MQTT 可显式清除。修改连接目标时需要重新提供或清除密码。
