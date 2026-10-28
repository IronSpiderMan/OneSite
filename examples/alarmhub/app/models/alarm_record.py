"""Illustrative alarm records; the example does not send notifications."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from onesite.config import OneSiteConfig
from sqlmodel import Field, SQLModel
from .rule import AlarmLevel


class AlarmStatus(str, Enum):
    active = "active"
    acknowledged = "acknowledged"
    recovered = "recovered"
    __i18n__ = {"zh": {"active": "告警中", "acknowledged": "已确认", "recovered": "已恢复"}}


class AlarmRecord(SQLModel, table=True):
    __onesite__ = OneSiteConfig(
        icon="AlarmClock",
        page_edit=True,
        permissions={"user": "r", "admin": "r", "developer": "crud"},
        translations={
            "zh": {
                "name": "告警记录",
                "fields": {
                    "title": "名称",
                    "note": "告警内容",
                    "rule_id": "规则",
                    "level": "等级",
                    "status": "状态",
                    "created_at": "创建时间",
                },
            }
        },
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    note: str
    rule_id: int = Field(foreign_key="rule.id")
    level: AlarmLevel = AlarmLevel.high
    status: AlarmStatus = AlarmStatus.active
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
