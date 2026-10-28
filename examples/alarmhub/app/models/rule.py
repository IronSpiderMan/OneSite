"""Business rules reference plugin-owned points and native conditions."""

from enum import Enum
from typing import Optional
from onesite.config import OneSiteConfig
from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel


class RuleSource(str, Enum):
    value = "value"
    ac = "ac"
    __i18n__ = {"zh": {"value": "点位值", "ac": "A&C 告警"}}


class AlarmLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"
    __i18n__ = {"zh": {"low": "一般", "medium": "中等", "high": "重要", "critical": "紧急"}}


class Rule(SQLModel, table=True):
    __table_args__ = (
        CheckConstraint(
            "(source_type = 'value' AND opcua_node_id IS NOT NULL AND opcua_ac_id IS NULL) OR "
            "(source_type = 'ac' AND opcua_ac_id IS NOT NULL AND opcua_node_id IS NULL)",
            name="ck_rule_plugin_source",
        ),
    )
    __onesite__ = OneSiteConfig(
        icon="GitFork",
        page_edit=True,
        permissions={"user": "r", "admin": "r", "developer": "crud"},
        translations={
            "zh": {
                "name": "告警规则",
                "fields": {
                    "title": "名称",
                    "description": "描述",
                    "category_id": "告警分类",
                    "source_type": "规则来源",
                    "opcua_node_id": "OPC UA 点位",
                    "opcua_ac_id": "OPC UA A&C",
                    "threshold": "告警阈值（大于）",
                    "level": "告警等级",
                    "is_enabled": "启用",
                },
            }
        },
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(unique=True, index=True)
    description: Optional[str] = None
    category_id: int = Field(foreign_key="category.id")
    source_type: RuleSource = RuleSource.value
    opcua_node_id: Optional[int] = Field(
        default=None,
        foreign_key="opcua_node.id",
        sa_column_kwargs={"info": {"site_props": {"visible_when": {"source_type": ["value"]}}}},
    )
    opcua_ac_id: Optional[int] = Field(
        default=None,
        foreign_key="opcua_ac.id",
        sa_column_kwargs={"info": {"site_props": {"visible_when": {"source_type": ["ac"]}}}},
    )
    threshold: Optional[float] = Field(
        default=None,
        sa_column_kwargs={"info": {"site_props": {"visible_when": {"source_type": ["value"]}}}},
    )
    level: AlarmLevel = AlarmLevel.high
    is_enabled: bool = True

    def _validate(self, changes):
        source = changes.get("source_type", self.source_type)
        node = changes.get("opcua_node_id", self.opcua_node_id)
        ac = changes.get("opcua_ac_id", self.opcua_ac_id)
        if source == RuleSource.value:
            if node is None:
                raise ValueError("点位规则必须选择 OPC UA 点位")
            changes["opcua_ac_id"] = None
        elif source == RuleSource.ac:
            if ac is None:
                raise ValueError("A&C 规则必须选择条件")
            changes.update(opcua_node_id=None, threshold=None)
        else:
            raise ValueError("不支持的规则来源")

    def on_before_create(self):
        changes = {}
        self._validate(changes)
        for name, value in changes.items():
            setattr(self, name, value)

    def on_before_update(self, changes):
        self._validate(changes)
