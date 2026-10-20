# 代码生成模块职责

`onesite.generator` 保留对外的生成入口，`codegen/pipeline.py` 按顺序调用
`codegen/phases/` 中的阶段。阶段负责协调配置加载、模型同步、关系解析、模板生成
和生成结果整理。

## 模型元数据

`codegen/introspect.py` 的 `get_model_fields()` 读取 SQLModel 表模型，组装
`FieldDefinition` 和 `ModelIntrospectResult`。独立的配置校验与规范化放在
`codegen/metadata/`，避免报表、权限等功能都堆积在字段解析模块中。

| 模块 | 职责 |
| --- | --- |
| `metadata/fields.py` | Pydantic/SQLModel 类型判断、可空类型解包、数值约束和字段元数据读取 |
| `metadata/json_schema.py` | JSON 子模型结构、嵌套布局、条件字段及根字段引用 |
| `metadata/permissions.py` | 模型 CRUD、字段 CRU、菜单可见性及角色顺序 |
| `metadata/reports.py` | 报表输入、筛选、聚合与访问范围校验 |
| `metadata/dashboard_metrics.py` | 模型级与项目级仪表盘指标共用的校验与规范化 |
| `metadata/display.py` | 多项展示字段及展示参数校验 |
| `metadata/tracking.py` | 操作追踪声明的校验与稳定排序 |

元数据模块不生成文件，也不依赖流水线阶段或 `introspect.py`。
`visualizations.py` 直接使用指标规范化模块，避免经由模型解析入口调用私有实现。
新增独立配置能力时，将校验放到对应元数据模块，再由解析入口组装结果。

## 共用基础工具

`codegen/naming.py` 提供 snake_case、PascalCase 和复数命名规则，供元数据解析
及生成阶段共用。

`codegen/file_utils.py` 提供内容比较、写入、复制和目录同步。
`assets.py` 与 `custom_backend.py` 都依赖这一层，后者无需加载整个资源同步模块。
Python 文件同步与完整目录同步保留各自的文件筛选和清理规则。

## 兼容与验证

`onesite.generator`、`codegen.introspect.get_model_fields` 等入口保持不变。
原先由 `introspect.py`、`assets.py`、`phases/base.py` 提供的已迁移函数和常量
通过显式导入继续保留，旧调用方无需调整导入路径。

此结构调整不修改配置语义、生成模板或阶段执行顺序。相关回归测试位于 `tests/`：

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src/onesite/codegen
```
