from enum import Enum
from typing import Optional
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class RuleType(str, Enum):
    NOT_NULL = "not_null"
    UNIQUE = "unique"
    RANGE = "range"
    REGEX = "regex"
    REFERENCE = "reference"


class RuleSeverity(str, Enum):
    WARN = "warn"
    ERROR = "error"
    CRITICAL = "critical"


class DataQualityRule(SQLModel, table=True):
    __tablename__ = "data_quality_rule"

    __onesite__ = {
        "icon": "ShieldCheck",
        "actions": {
            "toggle_enabled": {"toggle": "is_enabled", "permissions": "du"},
        },
        "translations": {
            "zh": {
                "name": "质量规则",
                "fields": {
                    "name": "规则名称",
                    "dataset_id": "所属数据集",
                    "field_name": "校验字段",
                    "rule_type": "规则类型",
                    "severity": "严重级别",
                    "is_enabled": "是否启用",
                    "params": "规则参数",
                    "description": "描述",
                },
                "enums": {
                    "rule_type": {
                        "not_null": "非空", "unique": "唯一", "range": "取值范围",
                        "regex": "正则", "reference": "引用完整性",
                    },
                    "severity": {"warn": "警告", "error": "错误", "critical": "严重"},
                },
            }
        },
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(
        index=True,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    dataset_id: int = Field(
        foreign_key="dataset.id",
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    field_name: str
    rule_type: RuleType = Field(default=RuleType.NOT_NULL)
    severity: RuleSeverity = Field(default=RuleSeverity.WARN)
    is_enabled: bool = Field(default=True)
    # 规则参数,如 range 的 min/max、regex 的 pattern
    params: Optional[dict] = Field(
        default=None,
        sa_column=Column(
            JSON, nullable=True,
            info={"site_props": {"component": "json"}},
        ),
    )
    description: Optional[str] = None
