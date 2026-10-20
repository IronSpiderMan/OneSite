# TimescaleDB 设备模块设计

## 结论

`device_timeseries` 采用六张最小业务表：

1. `device_model`
2. `device_model_field`
3. `device`
4. `device_field`
5. `device_history`
6. `device_latest`

项目通过 `plugins=["device_timeseries"]` 启用模块。未启用时不生成这些模型。

`device_model_field` 和 `device_field` 是从属资源，不提供顶层菜单入口：
前者嵌入 `device_model` 详情页维护，后者嵌入 `device` 详情页维护；其后端 API
继续保留，供业务集成和设备反写使用。`device_field` 只能由
创建设备时自动生成，不能通过接口或嵌入页手工添加；编辑时其设备、模型字段、
名称、数据类型和单位均为只读快照。

## 表结构

### `device_model`

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `id` | int | 主键 |
| `name` | string | 必填、唯一、索引 |
| `description` | string | 可空 |

`name` 同时作为展示名称和业务标识，不再单独设置 `identifier`。模型下存在设备时，默认 hook 禁止新增、修改、删除模型字段（包含跨模型移动）。模型名称和说明仍可修改；已有设备不能直接更换设备模型。

### `device_model_field`

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `id` | int | 主键 |
| `device_model_id` | int | FK → `device_model.id` |
| `name` | string | 模型内唯一 |
| `dtype` | enum | 必填 |
| `unit` | string | 可空 |
| `enum_values` | JSON | 仅 enum 使用 |
| `min_value` | decimal | 仅数值类型使用 |
| `max_value` | decimal | 仅数值类型使用 |

支持 `str/bool/float32/float64/int8/int32/int64/uint8/enum`。唯一约束为 `(device_model_id, name)`。

### `device`

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `id` | string | 主键，自动生成 UUID v4 字符串，接口只读 |
| `name` | string | 必填、唯一、索引，设备业务名称 |
| `device_model_id` | int | FK → `device_model.id` |
| `protocol` | enum | `opcua/mqtt/modbus` |
| `collection_interval_seconds` | int | 默认 60，必须大于 0 |
| `timeout` | int | 默认 60 秒，必须 > 0；仅保存离线超时配置，不实现判断逻辑 |
| `heartbeat_interval_seconds` | int | 默认 60 秒，必须 > 0；设备所有字段共用 |

`id` 使用 Python 默认工厂生成 UUID v4 字符串，创建表单无需填写，外键仍为 string。
这不是数据库 server default；直接 SQL 插入设备时仍须提供 ID。
`name` 是唯一业务名称，可以修改，不改变历史数据关联的设备 ID。
订阅型协议可以忽略采集周期；周期上报使用设备的 `collection_interval_seconds`，
变化加心跳模式使用设备的 `heartbeat_interval_seconds`。插件仅保存这些配置，不运行采集或离线检测。

### `device_field`

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `device_id` | string | FK → `device.id`，联合主键 |
| `device_model_field_id` | int | FK → `device_model_field.id` |
| `name` | string | 从模型字段复制，联合主键，只读 |
| `dtype` | string | 从模型字段复制，只读 |
| `unit` | string | 从模型字段复制，可空，只读 |
| `address` | string | 可空 |
| `attribute` | enum | `read/subscribe/read_subscribe/write` |
| `value` | JSON | 可空，持久化格式为 `{"value": value}`；读响应为字符串 |
| `report_mode` | enum | `periodic/change/change_heartbeat` |
| `deadband` | decimal | 可空，必须 ≥ 0 |

没有独立整数 ID。联合主键为 `(device_id, name)`，另有唯一约束 `(device_id, device_model_field_id)`。`name/dtype/unit`
是创建设备字段时从模型字段生成的不可编辑快照，用于高频时序查询和界面展示；模型字段一旦被设备使用便不可修改，因此不会产生漂移。周期模式直接使用设备的 `collection_interval_seconds`，不再增加字段级 report interval。

### `device_history`

TimescaleDB hypertable：

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `device_id` | string | FK → `device.id` |
| `metric` | string | 与 device_id 组成联合外键 → `device_field(device_id, name)` |
| `value` | JSON | 必填，格式为 `{"value": value}` |
| `reported_at` | timestamptz | 必填、TimescaleDB 时间列 |

复合主键为 `(device_id, metric, reported_at)`。

默认生命周期为：chunk 1 天、7 天后压缩、保留 90 天。

### `device_latest`

普通 PostgreSQL 表：

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `device_id` | string | FK → `device.id` |
| `metric` | string | 与 device_id 组成联合外键 → `device_field(device_id, name)` |
| `value` | JSON | 必填，格式为 `{"value": value}` |
| `reported_at` | timestamptz | 必填 |

复合主键为 `(device_id, metric)`，因此每个设备字段只有一条数据。写入 history 后使用带时间条件的 upsert 更新 latest，旧的乱序数据不能覆盖新值。

## 关系

```text
device_model
├── device_model_field
└── device
    └── device_field
        ├── device_history
        └── device_latest
```

## 原生级联删除

插件通过 SQLModel 的 `Field(foreign_key="device.id", ondelete="CASCADE")`
配置 `device_field`、`device_history`、`device_latest` 的设备外键。
history/latest 到 device_field 的联合外键也保留 `ON DELETE CASCADE`。

- 删除设备时，数据库自动删除其字段、历史数据和最新值；无需项目编写清理 hook。
- 通过 ORM 或直接 SQL 删除设备均生效，删除及级联清理在同一事务中，可一起回滚。
- 其他设备的数据以及共享的 device_model、device_model_field 不被删除。
- 数据库级联不会逐条执行子模型的删除 hook；外部系统清理应在设备级 hook 中处理。
- 额外的项目自定义表若仍以非级联外键引用设备或字段，仍可能阻止设备删除。

## 默认 hook

启用插件即生成以下默认行为，无需项目手写 hook：

- `Device.on_before_create`：检查模型存在，并锁定模型行。
- `Device.on_after_create`：读取模型字段，按名称、类型、单位生成设备字段，
  默认地址为模型字段名；已有字段按模型字段 ID 跳过，重复调用不重复创建。
  使用同一 session 添加、flush，不独立 commit；设备创建失败时一起回滚。
  该内部初始化直接使用 ORM，不经过禁止手工创建的 hook。
- `Device.on_before_update`：禁止直接更换设备模型。
- `DeviceModelField.on_before_create/update/delete`：模型已有设备时拒绝字段增删改；
  移动字段同时检查原模型和目标模型。与设备创建使用同一个父模型行锁，
  PostgreSQL 默认 READ COMMITTED 隔离级别下将两种操作串行化。
- `DeviceField.on_before_create`：拒绝通过通用 CRUD 手工创建。

这些是生成 CRUD 调用的应用层 hook，不是数据库触发器。直接 SQL 或绕过 CRUD 的
ORM 写入不会自动执行冻结规则。更高事务隔离级别需自行处理快照和事务重试。

## value 的读写转换

`DeviceField` 默认携带 `override_field("value")` 和
`override_field("value", direction="write")`：

- 读响应按 `device_id + name=metric` 查询 `device_latest.value`，不读取设备字段里保存的反写值；没有遥测记录时显示空字符串。提取遥测 JSON 的 `value`；浮点数显示两位小数，其余转字符串，空值显示空字符串。
- 更新接口接受标量字符串；按 dtype 将 float、整数及 bool 转回原生值，并包为
  `{"value": ...}`。布尔文本接受 true/false、1/0（忽略大小写和首尾空格）。
- 输入 None 或空白字符串时保留原值，不代表清空字段。
- 读格式化不修改数据库原值；再次提交显示值会按显示精度保存。
- `DeviceField.value` 持久化值用于反写，页面“当前值”通过异步读 resolver 查询 `device_latest.value`，列表、详情和嵌入关系页共用此逻辑；查询不修改设备字段、不调用反写适配器。刷新或重新请求时读取最新遥测，不提供自动轮询。

history/latest 的值结构、类型、枚举及范围校验仍须由采集入口负责。
PostgreSQL 历史写入通过数据库触发器同步 latest，同一事务内完成。

## 设备反写

当 `DeviceField.attribute == "write"` 时，更新其 `value`（格式为
`{"value": ...}`）会先按 `dtype` 校验，再调用项目适配器：

```python
app.integrations.device_timeseries.write_device_field(
    session=session,
    field=device_field,
    value=value,
    current_user=current_user,
)
```

适配器由项目实现，可对接协议驱动或网关。默认模板不含 EdgeFlow 导入、调用或配置。
适配器抛出异常时数据库更新回滚，但数据库回滚不能撤销已经发送到物理设备的命令；
需要可靠投递时应由项目实现命令确认、幂等与重试机制。

## 已有项目升级

- 项目源模型同名文件会完全覆盖插件默认模型；已有覆盖文件需手工合入这些改动。
- `site sync` 生成代码不等于完成数据库迁移，已有数据库须单独迁移。
- 原有 device_field、device_history、device_latest 到 device.id 的外键需要迁移为
  `ON DELETE CASCADE`，并确认 history/latest 到 device_field 的联合外键同样配置级联。
  仅修改模型或运行 sync 不会改写数据库已有约束。生产环境执行前应备份数据；
  SQLite 验证环境需要显式启用 `PRAGMA foreign_keys=ON`。
- 现有 string 设备 ID 可以保留；UUID 默认工厂仅影响新建设备。
- 添加 name 唯一约束前，必须先处理重复业务名称。
- 给 device 新增 timeout 和 heartbeat_interval_seconds，并为旧设备回填正值
  （默认均为 60）。迁移原设备字段的心跳时，若同一设备有不同值，需先确定统一值，
  不应静默选择；完成回填及采集端适配后再移除旧列。
- 模型字段 CHECK 约束使用 ORM 实际存储的枚举名称（ENUM、FLOAT32 等），
  enum_values 的 None 持久化为 SQL NULL。已有数据库需同步修正约束，
  并将不适用的 JSON null 转换为 SQL NULL。
- 此前创建但没有字段的设备不会因 sync 自动补齐；可在维护事务中调用
  `Device.on_after_create(session)` 幂等补齐。
- 实际设备字段主键为 `(device_id, name)`，history/latest 使用 metric 引用名称，
  并非旧文档中的 device_field_id；按旧文档自建的数据库需要另行迁移。
