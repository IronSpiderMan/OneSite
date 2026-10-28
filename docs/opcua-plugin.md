# OPC UA 插件

在 `site_config.py` 的 `SiteConfig` 中加入 `plugins=["opcua"]`，然后执行
`site sync --install`。已有插件时将 `"opcua"` 加入原列表。

## 默认资源

- `OpcuaServer`：连接地址、用户名密码、应用证书、安全策略和运行参数。
- `OpcuaNode`：所属 Server、NodeId、名称、描述、启用开关，以及枚举采集模式
  `subscribe/poll/manual` 和对应间隔。
- `OpcuaAc`：所属 Server、事件订阅入口、ConditionId、名称、描述和启用开关。

Server 是顶层资源；Node 和 AC 不生成独立导航或详情路由，在 Server 详情页的
两个关联标签中维护。名称在各自 Server 内唯一；同一地址的 Server 可以配置
不同身份。Node 的 `(opcua_server_id, nodeid)` 和 AC 的
`(opcua_server_id, event_notifier_nodeid, condition_id)` 有数据库唯一约束。

默认 developer 可执行 CRUD；admin 只读；user 无访问权限。默认导航仅对
developer 显示。项目可以在 `app/models/opcua_server.py`、`opcua_node.py`、
`opcua_ac.py` 提供同名模型覆盖默认配置；Browse 要求保留模型名称、资源名称、
整数主键和所需连接字段，缺少字段时生成会给出错误。

## 默认运行参数

新建表单和后端模型使用以下默认值，可按设备负载和时效要求调整：

| 资源 | 参数 | 默认值 |
| --- | --- | --- |
| Server | 请求超时 `request_timeout_seconds` | 10 秒 |
| Server | 重连间隔 `reconnect_interval_seconds` | 5 秒 |
| Server | 订阅发布间隔 `publishing_interval_ms` | 1000 毫秒 |
| Node | 采样间隔 `sampling_interval_ms` | 1000 毫秒 |
| Node | 轮询间隔 `polling_interval_seconds` | 1 秒 |

Node 默认使用订阅模式。采样间隔允许设为 0；其余间隔和超时必须大于 0。
默认值应用于新建记录，不覆盖已有记录或项目自定义模型中的默认值。

## Browse

Server 详情页的“浏览节点”按钮使用保存的连接配置访问服务器，提供：

- 按需加载的节点目录、面包屑、NodeId 定位、当前层搜索和类型筛选。
- 变量点位与 A&C 条件的跨目录多选、批量添加、已添加项识别和失败重试。
- 自定义 ConditionType 子类型识别。
- 使用命名空间 URI 的稳定地址保存点位与条件，支持 `nsu=URI;s=标识` 定位。
- A&C 默认事件订阅入口 `i=2253`，添加前可以修改。
- 添加成功后自动刷新 Server 详情页的关联列表。

Browse API 为 `GET /api/v1/opcua/{server_id}/browse?nodeid=i=84`，遵守 Server
模型的读取权限和所有者范围。批量添加通过普通 Node/AC CRUD API 完成，分别
遵守子模型的创建权限；界面还要求读取权限，以便核对已有配置。

只有在地址空间中公开的 Condition 实例可以被发现；仅通过事件公开的条件
仍然需要手工配置。

## 认证和证书

用户认证使用 `OpcuaAuthType`，安全策略使用 `OpcuaSecurityPolicy`，消息安全
模式使用 `OpcuaSecurityMode`。当前支持匿名、用户名密码，以及
`None` 或 `Basic256Sha256` 策略。启用后者时必须选择 `Sign` 或
`SignAndEncrypt`，并提供客户端证书、客户端私钥和受信任的服务器证书。
应用 URI 留空时尝试从客户端证书读取。

私钥使用私有上传。密码不会出现在读取响应中，编辑时留空保留旧密码。
浏览失败只返回通用错误，不返回凭据、证书路径或远端异常文本。

## 运行边界

本插件当前提供配置模型、CRUD、页面和按需 Browse，不自动启动持续采集、
事件订阅、重连任务或告警通知。`reconnect_interval_seconds`、
`publishing_interval_ms`、采集模式和点位间隔保存为项目运行服务使用的配置；
`request_timeout_seconds` 已用于 Browse 请求。启用开关不阻止手动 Browse。

插件不依赖 `device_timeseries`，也不自动创建 AlarmHub Trigger。项目可以使用
生成的 `app.core.opcua.create_client(server)` 建立客户端，并在自己的运行服务中
接入采集、告警处理或 `device_timeseries`。

关闭插件并重新同步后，默认模型和 Browse 生成代码、路由及依赖会被移除；
项目自定义的同名源模型会保留。数据库表是否保留由生成的迁移决定。
