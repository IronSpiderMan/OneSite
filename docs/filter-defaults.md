# 筛选默认值

筛选默认值独立于 `Field(default=...)`，仅影响页面查询，用户可以修改或清空。

## 列表页

在字段的 `site_props` 中指定 `is_search_field` 和 `filter_default`：

```python
status: str = Field(sa_column_kwargs={"info": {"site_props": {
    "is_search_field": True,
    "filter_default": "active",
}}})
```

支持字符串、布尔值、枚举、多选枚举数组、外键 ID、时间，以及日期和日期时间范围。普通数值字段目前没有列表筛选控件，不能配置列表筛选默认值；数值可用于可视化 select 和 number_range。

```python
# 日期 / 日期时间字段
"filter_default": {"period": "this_month"}
# 或固定范围（可省略其中一个边界）
"filter_default": {"start": "2026-10-01", "end": "2026-10-20"}
# 布尔字段
"filter_default": False
# 多选枚举字段
"filter_default": ["active", "pending"]
```

日期时间列表控件按日期筛选，范围两端覆盖当天。相对时间支持 `today`、`yesterday`、`this_week`、`last_week`、`this_month`、`last_month`、`last_7_days`、`last_30_days`。周从周一开始，最近 N 天包含今天，使用浏览器本地日历时间。

首次进入时填入默认值，首次请求直接应用。返回列表时恢复之前的条件，包括主动清空的状态。“清空”移除条件，“重置”恢复默认值并重新计算相对日期。仪表盘图表筛选区只提供“重置筛选”，恢复默认条件；没有默认值时清空筛选。嵌入列表的固定范围优先于默认值。没有读取权限的字段不显示，也不会随列表查询发送。

## 项目级可视化

在 `chart(..., filters=[...])` 的筛选声明中增加 `default`：

```python
filters=[
    {"key": "status", "field": "status", "type": "select", "default": "active"},
    {"key": "levels", "field": "level", "type": "multi_select", "default": ["LOW"]},
    {"key": "created", "field": "created_at", "type": "date_range", "default": {"period": "this_month"}},
    {"key": "amount", "field": "amount", "type": "number_range", "default": {"min": 0}},
]
```

固定日期范围使用 `start` / `end`，数值范围使用 `min` / `max`。`False` 和 `0` 是有效默认值。默认值通过可视化元数据返回；初始查询和控件使用相同的值，清空后不会自动重新填入。

旧版模型 `visualize.filters` 的枚举及外键筛选也支持 `default` 固定值。

生成时校验默认值类型、枚举选项、范围顺序及相对时间周期，错误信息包含模型/字段或可视化筛选名称。默认值不是访问控制，强制范围应由后端权限实现。

### 普通枚举字段的多选筛选

普通 enum 字段配置 `"is_search_field": True` 后，列表筛选默认支持多选，无需设置 `is_multi_select`。创建和编辑表单仍然单选。

同字段的多个选项按 OR 匹配，不同字段之间按 AND 组合；清空表示不限。接口使用重复参数，例如 `?status=active&status=pending`，原有单值 `?status=active` 仍然有效。

`filter_default` 可以是单个枚举值，也可以是枚举值数组。数组 enum 字段保留原有的“包含全部所选值”筛选语义。
