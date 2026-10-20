-- Sample hierarchy for the "Documents by folder" dashboard tree.
-- IDs are fixed and inserts are idempotent so this fixture can be replayed.

BEGIN;

INSERT OR IGNORE INTO asset_folder (id, name, parent_id, description) VALUES
    (1001, '数据平台', NULL, '数据平台相关资产'),
    (1002, '业务分析', NULL, '面向业务分析师的数据资产'),
    (1003, '归档资料', NULL, '历史资料与归档'),
    (1101, '数据接入', 1001, '采集、同步和数据源接入'),
    (1102, '数据治理', 1001, '质量、血缘和标准规范'),
    (1201, '销售分析', 1002, '销售主题分析资产'),
    (1202, '用户增长', 1002, '用户与增长主题资产'),
    (1111, '批处理', 1101, '离线批处理接入'),
    (1112, '实时流', 1101, '实时流式接入');

-- Keep roots compatible with the generated API's parent_id=0 sentinel even
-- when this fixture repairs data inserted by an older version of the demo.
UPDATE asset_folder SET parent_id = NULL WHERE id IN (1001, 1002, 1003);

INSERT OR IGNORE INTO asset_document (id, name, folder_id, content) VALUES
    (2001, 'MySQL 接入规范', 1101, '连接配置、权限要求以及增量同步约定。'),
    (2002, 'Kafka Topic 命名规范', 1112, '实时主题命名、分区与保留策略。'),
    (2003, '夜间批任务清单', 1111, '每日夜间运行的核心数据同步任务。'),
    (2004, '数据质量检查手册', 1102, '完整性、唯一性与及时性检查说明。'),
    (2005, '核心指标口径', 1102, 'GMV、订单量和活跃用户等指标定义。'),
    (2006, '销售日报说明', 1201, '销售日报字段及刷新时间说明。'),
    (2007, '区域业绩看板', 1201, '区域维度业绩数据与使用指南。'),
    (2008, '用户分层模型', 1202, '用户生命周期分层规则。'),
    (2009, '增长实验记录', 1202, '增长实验设计、指标和实验结论。'),
    (2010, '2025 年历史口径', 1003, '历史指标口径归档，仅供追溯。');

-- Dense leaf data: 数据接入 has 25 documents in total, intentionally
-- exceeding the configured leaf page_size=20 to demonstrate "Load more".
INSERT OR IGNORE INTO asset_document (id, name, folder_id, content) VALUES
    (2101, 'PostgreSQL 接入指南', 1101, 'PostgreSQL 数据源连接与同步配置。'),
    (2102, 'Oracle CDC 配置说明', 1101, 'Oracle 增量采集与日志配置要求。'),
    (2103, 'SQL Server 同步手册', 1101, 'SQL Server 全量和增量同步流程。'),
    (2104, 'MongoDB 采集规范', 1101, 'MongoDB 集合采集和字段映射规范。'),
    (2105, 'Redis 数据抽取说明', 1101, 'Redis 键空间扫描与数据落库说明。'),
    (2106, 'Elasticsearch 导入指南', 1101, '索引数据导入及映射转换说明。'),
    (2107, 'S3 对象存储接入', 1101, '对象存储文件发现与增量加载策略。'),
    (2108, 'OSS 文件同步规范', 1101, '文件同步目录、格式和命名约定。'),
    (2109, 'FTP 数据交换手册', 1101, 'FTP 交换目录与文件校验约定。'),
    (2110, 'SFTP 安全接入指南', 1101, '密钥认证、目录权限和传输要求。'),
    (2111, 'HTTP API 采集规范', 1101, '分页、限流和失败重试策略。'),
    (2112, 'GraphQL 数据接入', 1101, 'GraphQL 查询模板与游标分页说明。'),
    (2113, 'Webhook 事件接收规范', 1101, '事件签名、去重和重放处理说明。'),
    (2114, 'Excel 文件导入模板', 1101, '表头、字段类型和数据校验规则。'),
    (2115, 'CSV 批量导入规范', 1101, '编码、分隔符和空值处理约定。'),
    (2116, 'JSON Lines 接入说明', 1101, 'JSONL 文件结构及字段演进策略。'),
    (2117, 'Parquet 文件加载指南', 1101, 'Parquet 分区与压缩格式要求。'),
    (2118, 'Avro Schema 管理规范', 1101, 'Schema 注册、兼容与升级约定。'),
    (2119, '数据源连通性检查', 1101, '网络、账号和权限的检查清单。'),
    (2120, '采集任务上线流程', 1101, '采集任务评审、发布与回滚步骤。'),
    (2121, '接入失败排查手册', 1101, '常见连接和数据格式问题排查。'),
    (2122, '敏感数据接入要求', 1101, '敏感字段识别、脱敏和授权要求。'),
    (2123, '跨地域同步说明', 1101, '跨地域链路、延迟和容灾配置。'),
    (2124, '第三方数据验收清单', 1101, '第三方数据质量与交付验收项目。'),
    (2201, '日终订单同步任务', 1111, '订单主题日终批处理任务说明。'),
    (2202, '客户主数据合并任务', 1111, '客户主数据去重与合并规则。'),
    (2203, '商品维表刷新任务', 1111, '商品维度全量刷新计划。'),
    (2204, '库存快照生成任务', 1111, '每日库存快照生成与核对说明。'),
    (2205, '财务月结批处理', 1111, '财务月结数据处理依赖与步骤。'),
    (2206, '历史数据回灌方案', 1111, '历史分区回灌及影响控制。'),
    (2207, '离线任务依赖图', 1111, '核心离线任务上下游依赖说明。'),
    (2208, '批任务重跑规范', 1111, '失败任务重跑与幂等性要求。'),
    (2209, '数据分区清理策略', 1111, '历史分区保留与定期清理规则。'),
    (2210, '批处理资源配额', 1111, '队列、CPU 与内存资源配额说明。'),
    (2211, '节假日调度日历', 1111, '节假日批任务暂停和补跑安排。'),
    (2212, '批处理 SLA 清单', 1111, '关键任务完成时限及负责人。'),
    (2301, '用户行为实时流', 1112, '用户行为事件实时采集说明。'),
    (2302, '订单状态变更流', 1112, '订单状态事件格式和顺序保证。'),
    (2303, '支付结果通知流', 1112, '支付结果事件与异常补偿机制。'),
    (2304, '设备遥测数据流', 1112, '设备指标采样和实时传输规范。'),
    (2305, '日志实时解析规则', 1112, '应用日志解析与字段提取规则。'),
    (2306, '实时告警事件规范', 1112, '告警事件等级、路由和抑制规则。'),
    (2307, 'Flink 作业发布流程', 1112, '实时作业发布、灰度与回滚流程。'),
    (2308, 'Kafka 消费组规范', 1112, '消费组命名、扩缩容和位点管理。'),
    (2309, '实时流量监控指标', 1112, '吞吐、延迟和积压监控指标。'),
    (2310, '迟到事件处理策略', 1112, '事件时间、水位线和迟到数据策略。'),
    (2311, '实时去重方案', 1112, '基于业务键的实时事件去重方案。'),
    (2312, '流式数据质量规则', 1112, '实时完整性与异常值检测规则。');

-- Volume data for inspecting a tree with roughly one hundred leaf records.
-- Keep these generated records deterministic and idempotent so the fixture
-- can still be replayed safely.
WITH RECURSIVE sequence(n) AS (
    SELECT 1
    UNION ALL
    SELECT n + 1 FROM sequence WHERE n < 35
)
INSERT OR IGNORE INTO asset_document (id, name, folder_id, content)
SELECT
    3000 + n,
    '数据接入方案示例 ' || printf('%02d', n),
    1101,
    '用于验证大量 leaf node 展示、滚动和分页加载的接入方案示例。'
FROM sequence;

WITH RECURSIVE sequence(n) AS (
    SELECT 1
    UNION ALL
    SELECT n + 1 FROM sequence WHERE n < 12
)
INSERT OR IGNORE INTO asset_document (id, name, folder_id, content)
SELECT
    3100 + n,
    '批处理作业示例 ' || printf('%02d', n),
    1111,
    '用于验证批处理目录下密集 leaf node 的作业说明。'
FROM sequence;

WITH RECURSIVE sequence(n) AS (
    SELECT 1
    UNION ALL
    SELECT n + 1 FROM sequence WHERE n < 12
)
INSERT OR IGNORE INTO asset_document (id, name, folder_id, content)
SELECT
    3200 + n,
    '实时流任务示例 ' || printf('%02d', n),
    1112,
    '用于验证实时流目录下密集 leaf node 的任务说明。'
FROM sequence;

COMMIT;
