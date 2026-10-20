# OneSite 可视化功能重设计

## 结论

把可视化从模型的 `__onesite__` 中移出，在项目根目录增加独立的
`visualizations.py`。模型只描述业务数据；可视化配置只做三件事：

1. 选择图形预设，例如 `line.smooth`、`pie.half_donut`；
2. 把预设要求的输入槽位映射到模型字段或聚合表达式；
3. 声明筛选、权限和页面位置。

OneSite 在 `site sync` 时将配置编译成通用查询计划和 ECharts 配置。用户不需要
理解 `series`、`dataset.encode`、SQL `GROUP BY` 或前后端数据转换。

## 设计目标

- 业务模型与图表完全解耦；删除模型后才影响引用它的图表。
- 相同数据形态的图表共享查询和响应，只切换样式预设。
- 用户关注“图需要什么输入、输入来自哪个模型字段”。
- 编译期发现字段、类型、聚合、关联路径和权限错误。
- 支持从简单统计图逐步扩展到树、桑基、关系图等复杂结构。
- Dashboard、数据报表页和未来的自定义页面使用同一套图表运行时。

## 一、三个核心概念

### 1. 输入契约（Data Contract）

输入契约定义一组语义槽位及其类型，与具体样式无关。例如 `xy` 只要求 `x` 和
`y`；所有基础折线、平滑折线和基础面积图都可以消费它。

### 2. 图形预设（Chart Preset）

预设负责把输入契约转换为 ECharts option。预设只能改变表现，不改变查询语义。

例如：

- `line.basic`、`line.smooth`、`line.area` 都使用 `xy`；
- `line.stacked`、`line.stacked_area`、`line.stacked_area_gradient` 都使用
  `xy_series`；
- `pie.donut`、`pie.rounded_donut`、`pie.half_donut` 都使用
  `category_value`。

因此，同一张图可以安全地在兼容预设之间切换，不重新设计数据查询。

### 3. 模型绑定（Data Binding）

绑定描述每个输入槽位来自哪个模型字段或聚合表达式。OneSite 根据绑定自动推导：

- `SELECT` 和 `GROUP BY`；
- 外键关联；
- 时间分桶；
- 排序、空值和缺失点处理；
- 返回数据的维度名称和类型。

## 二、第一版输入契约

| 契约 | 必填输入 | 可选输入 | 适用预设 |
| --- | --- | --- | --- |
| `xy` | `x`, `y` | `label`, `tooltip` | 基础/平滑折线、面积、基础散点 |
| `xy_series` | `x`, `series`, `y` | `label`, `tooltip` | 多折线、堆叠折线、堆叠面积、多类别散点 |
| `category_value` | `category`, `value` | `tooltip` | 饼、环、半环、漏斗 |
| `xyz` | `x`, `y`, `value` | `tooltip` | 笛卡尔热力图、气泡图 |
| `radar` | `indicator`, `series`, `value` | `max` | 雷达图 |
| `hierarchy` | `id`, `parent`, `name` | `value` | 树、矩形树、旭日图 |
| `links` | `source`, `target`, `value` | `source_name`, `target_name` | 桑基图 |
| `graph` | `node_id`, `node_name`, `source`, `target` | `node_value`, `edge_value`, `category` | 关系图 |

这里的 `series` 表示“系列名称”，不是让用户配置 ECharts 的 `series` 对象。

### 为什么多系列统一为 `x / series / y`

用户可能通过两种方式得到 N 条线：

1. 一个分类字段产生 N 个系列，例如按渠道统计销售额；
2. N 个数值指标产生 N 个系列，例如销售额、订单数、退款额。

两种写法都会被编译成长表：

```json
[
  {"x": "2026-08-01", "series": "销售额", "y": 1200},
  {"x": "2026-08-01", "series": "订单数", "y": 35},
  {"x": "2026-08-02", "series": "销售额", "y": 1600},
  {"x": "2026-08-02", "series": "订单数", "y": 42}
]
```

这样前端、接口和预设只处理一种多系列格式，不需要为动态类别和固定多个 Y 字段
分别实现一套逻辑。

## 三、用户配置 API

项目结构：

```text
my_project/                 # 项目根目录，名称可以是 app 或其他名称
├── app/                    # 开发者维护的源码
│   ├── models/
│   ├── integrations/
│   ├── tools/
│   └── utils/
├── generated/              # site sync 生成，可替换
│   ├── backend/
│   └── frontend/
├── deploy/
├── visualizations.py       # 所有项目级可视化定义
└── site_config.py
```

项目统一使用 `app/` 与 `generated/` 布局；顶层 `models/`、`backend/`、`frontend/` 不受支持。
默认结构。`visualizations.py` 位于项目根目录，与 `app/`、`generated/`、`deploy/`
平级，而不是放进生成目录。

建议的最小 DSL：

```python
from onesite.visualization import chart, count, dim, line, metric


visualizations = [
    chart(
        "daily_sales",
        title="每日销售额",
        preset=line.smooth,
        model="Order",
        x=dim("created_at", bucket="day"),
        y=metric("amount", aggregate="sum", label="销售额"),
    ),
]
```

`chart()` 接受的输入参数由 `preset` 对应的契约决定。这里选择 `line.smooth` 后，
同步器会明确提示它需要 `x` 和 `y`，并拒绝缺少输入或输入类型不兼容的配置。
各图表类型都提供同名的预设常量命名空间（`line`、`pie`、`scatter` 等），便于
编辑器自动补全；为了向后兼容，`"line.smooth"` 这样的字符串仍然有效。

### 单系列折线/面积图

只修改 `preset` 就能改变样式：

```python
chart(
    "daily_sales",
    title="每日销售额",
    preset="line.area",       # 也可换成 line.basic / line.smooth
    model="Order",
    x=dim("created_at", bucket="day"),
    y=metric("amount", aggregate="sum"),
)
```

### 多系列：由分类字段产生 N 条线

```python
chart(
    "sales_by_channel",
    title="各渠道销售趋势",
    preset="line.stacked_area_gradient",
    model="Order",
    x=dim("created_at", bucket="day"),
    series=dim("channel"),
    y=metric("amount", aggregate="sum"),
)
```

### 多系列：由 N 个指标产生 N 条线

```python
chart(
    "order_metrics",
    title="订单趋势",
    preset="line.stacked_area",
    model="Order",
    x=dim("created_at", bucket="day"),
    y=[
        metric("amount", aggregate="sum", label="销售额"),
        metric("id", aggregate="count", label="订单数"),
        metric("refund_amount", aggregate="sum", label="退款额"),
    ],
)
```

当 `y` 是列表时，编译器自动使用每个指标的 `label` 作为 `series`。用户不需要额外
写 `series`。

### 基础散点和多类别散点

```python
chart(
    "price_sales_scatter",
    title="价格与销量",
    preset="scatter.basic",
    model="Product",
    x=dim("price"),
    y=dim("sales_count"),
)

chart(
    "price_sales_by_category",
    title="各分类价格与销量",
    preset="scatter.category",
    model="Product",
    x=dim("price"),
    y=dim("sales_count"),
    series=dim("category.name"),  # 自动沿 FK 路径关联
)
```

### 饼图/环形图

```python
chart(
    "orders_by_status",
    title="订单状态分布",
    preset="pie.rounded_donut",  # 也可换 pie.donut / pie.half_donut
    model="Order",
    category=dim("status"),
    value=count(),
)
```

### 热力图

```python
chart(
    "weekday_hour_heatmap",
    title="下单时段热力图",
    preset="heatmap.cartesian",
    model="Order",
    x=dim("created_at", extract="hour"),
    y=dim("created_at", extract="weekday"),
    value=count(),
)
```

### 树图

```python
chart(
    "category_tree",
    title="商品分类",
    preset="tree.basic",
    model="Category",
    id=dim("id"),
    parent=dim("parent_id"),
    name=dim("name"),
    value=metric("products.id", aggregate="count"),
)
```

### 桑基图

```python
chart(
    "traffic_flow",
    title="页面流转",
    preset="sankey.basic",
    model="PageTransition",
    source=dim("from_page"),
    target=dim("to_page"),
    value=count(),
)
```

## 四、通用配置项

图的数据绑定之外只保留少量正交配置：

```python
chart(
    "sales_by_channel",
    title="各渠道销售趋势",
    preset="line.stacked_area",
    model="Order",
    x=dim("created_at", bucket="day"),
    series=dim("channel"),
    y=metric("amount", aggregate="sum"),
    where={"status": "paid"},
    filters=[
        {"key": "region", "field": "customer.region", "type": "select"},
        {"key": "range", "field": "created_at", "type": "date_range"},
    ],
    order_by=["x"],
    limit=1000,
    visible=["admin", "developer"],
    placement={"page": "dashboard", "span": 12, "order": 20},
    options={"legend": {"position": "bottom"}},
)
```

- `where` 是固定过滤条件，不能被前端修改；
- 时间字段可在 `where` 中使用相对时间范围，例如
  `where={"created_at": {"period": "today"}}`。支持 `today`、`yesterday`、
  `this_week`、`last_week`、`this_month` 和 `last_month`；范围按系统时区计算，
  并采用左闭右开区间，避免边界数据重复计入；
- `filters` 是允许用户交互的过滤器；
- `visible` 最终仍与所有参与模型的读取权限取交集；
- `placement` 只管页面布局；
- `options` 是受控的表现层覆盖，不允许改变 dataset、encode 或查询结果；
- 原生 ECharts option 仅作为高级逃生口，不能成为普通配置方式。

## 五、预设注册表

OneSite 内部维护注册表，而不是在模板里写一长串条件判断：

```python
PRESETS = {
    "line.basic": Preset(contract="xy", renderer="line", defaults={}),
    "line.smooth": Preset(contract="xy", renderer="line", defaults={"smooth": True}),
    "line.area": Preset(contract="xy", renderer="line", defaults={"area": True}),
    "line.stacked": Preset(contract="xy_series", renderer="line", defaults={"stack": True}),
    "pie.rounded_donut": Preset(contract="category_value", renderer="pie", defaults={"donut": True, "rounded": True}),
}
```

新增一种样式通常只需要增加一个预设；只有出现全新数据形态时才新增输入契约。

## 六、统一接口响应

后端不返回 ECharts option，而返回稳定的语义数据：

```json
{
  "visualization": "sales_by_channel",
  "contract": "xy_series",
  "dimensions": [
    {"name": "x", "type": "time"},
    {"name": "series", "type": "category"},
    {"name": "y", "type": "number", "unit": "CNY"}
  ],
  "rows": [
    {"x": "2026-08-01", "series": "web", "y": 1200},
    {"x": "2026-08-01", "series": "store", "y": 850}
  ],
  "meta": {
    "truncated": false,
    "timezone": "Asia/Shanghai"
  }
}
```

建议接口：

```text
GET  /api/v1/visualizations                 # 当前角色可见图表及元数据
GET  /api/v1/visualizations/{key}/options   # 筛选项、可用粒度等
POST /api/v1/visualizations/{key}/query     # 查询图表数据
```

统一接口替代现在每个模型生成一套 `get_stats` 的方式。数据响应与渲染库无关，也
便于 CSV 导出、缓存和测试。

## 七、生成链路

```text
visualizations.py
    ↓ 加载
输入契约校验
    ↓
模型字段/FK 路径解析
    ↓
查询计划 QueryPlan + 展示计划 VisualSpec
    ↓                         ↓
通用 FastAPI 查询运行时       ECharts 预设渲染器
    ↓                         ↓
语义 rows 响应 ───────────→ VisualizationCard
```

`QueryPlan` 和 `VisualSpec` 必须分开：前者决定查什么数据，后者决定数据怎么画。
切换同契约预设时只改变 `VisualSpec`。

## 八、编译期校验

`site sync` 至少检查：

- preset 是否存在，所需输入是否完整；
- 字段及 `a.b.c` FK 路径是否存在，关联是否有歧义；
- `y`、`value` 等数值输入是否为数值字段或数值聚合；
- `sum`/`avg` 不能作用于字符串字段；
- 散点图的 x/y 必须可比较，基础散点默认要求数值；
- 时间 bucket/extract 只能作用于日期时间字段；
- `id`/`parent` 和 `source`/`target` 类型是否匹配；
- 图表 key 唯一，筛选 key 唯一；
- 权限不能扩大任一参与模型的读取权限；
- `limit`、时间范围和最大节点数符合安全上限。

错误信息应面向输入槽位，例如：

```text
Visualization 'daily_sales': preset 'line.smooth' requires input 'y'.
Visualization 'orders_by_status': input 'value' must be numeric, got Order.status (enum).
Visualization 'sales_by_region': field path 'customer.region' is ambiguous; specify join path.
```

## 九、ECharts 前端实现建议

新引擎建议使用 ECharts，而不是继续扩展 Recharts：树、矩形树、旭日、桑基、关系
图、视觉映射和复杂热力图可以共用一个渲染体系。使用 `echarts/core` 按需注册图表、
坐标系和组件，避免全量打包。

前端只保留三个主要层次：

```text
VisualizationCard       标题、加载、空状态、错误、筛选、布局
ChartRuntime             dataset、主题、resize、事件、无障碍
PresetBuilder            contract rows → ECharts option
```

ECharts 的 `dataset` 和 `series.encode` 本身就是“数据维度到图形槽位”的映射模型，
与这里的输入契约天然匹配。OneSite 应替用户生成 encode，而不是把 encode 暴露给普通用户。

## 十、迁移策略

### 阶段 1：新增引擎，不破坏旧配置

- 新增 `visualizations.py`、契约注册表、编译器和统一接口；
- 新图表全部走 ECharts；
- 旧 `__onesite__["visualize"]` 仍能生成，但同步时显示弃用提示。
- Dashboard KPI 同样迁到 `visualizations.py` 的 `dashboard_metrics` 列表；
  每项通过 `model` 指定来源，仍复用该模型的 KPI endpoint 与权限校验。
- 旧 `__onesite__["dashboard_metrics"]` 仍能生成，但同步时显示弃用提示。

### 阶段 2：自动迁移常见配置

提供：

```bash
site migrate visualizations
```

将旧配置映射为：

- `label_field` → `category` 或 `series`；
- `value_field + aggregation` → `y` 或 `value`；
- `time_field` → `x=dim(..., bucket=...)`；
- `chart_type` → 对应 preset；
- `filters`、`visible`、`full_row` → 新的正交配置。

不能确定语义时生成带 TODO 的配置并给出原因，不静默猜测。

### 阶段 4：移除模型内 visualize

至少经过一个明确的兼容周期后，删除旧解析、模型级 `get_stats` 和旧 Dashboard
渲染分支。

## 十一、第一期范围

第一期建议只实现六个契约，已能覆盖绝大多数统计场景：

1. `xy`；
2. `xy_series`；
3. `category_value`；
4. `xyz`；
5. `hierarchy`；
6. `links`。

对应先交付折线/面积、堆叠折线/面积、散点、饼/环、热力、树和桑基。雷达和通用
关系图在契约稳定后加入，不让第一期被复杂元数据拖慢。

## 最重要的设计原则

用户配置的不是 ECharts，而是下面这个关系：

```text
图形预设要求的输入槽位 ← 模型字段 / 聚合表达式
```

OneSite 负责把这个关系编译成 SQL、接口响应和 ECharts option。这样图的样式越来越
多时，用户配置复杂度不会随之线性增长。

## 参考

- [Apache ECharts：数据集](https://echarts.apache.org/handbook/zh/concepts/dataset/)
- [Apache ECharts：堆叠折线图](https://echarts.apache.org/handbook/zh/how-to/chart-types/line/stacked-line/)
- [Apache ECharts：区域面积图](https://echarts.apache.org/handbook/zh/how-to/chart-types/line/area-line/)
- [Apache ECharts：基础散点图](https://echarts.apache.org/handbook/zh/how-to/chart-types/scatter/basic-scatter/)
- [Apache ECharts：在线示例](https://echarts.apache.org/examples/zh/index.html#chart-type-graphic)
