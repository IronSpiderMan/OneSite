from enum import Enum
from typing import Optional
from datetime import datetime
from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel


class SyncFrequency(str, Enum):
    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    REALTIME = "realtime"


class SyncTaskStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class SyncTask(SQLModel, table=True):
    __tablename__ = "sync_task"

    __onesite__ = {
        "icon": "RefreshCw",
        "refresh_interval": 30,
        "importable": True,
        "exportable": True,
        "import_key": "code",
        "actions": {
            "toggle_enabled": {"toggle": "is_enabled", "permissions": "du"},
        },
        "translations": {
            "zh": {
                "name": "同步任务",
                "fields": {
                    "code": "任务编码",
                    "name": "任务名称",
                    "data_source_id": "源数据源",
                    "dataset_id": "目标数据集",
                    "frequency": "同步频率",
                    "is_enabled": "是否启用",
                    "status": "状态",
                    "last_run_at": "最近运行",
                    "description": "描述",
                },
                "enums": {
                    "frequency": {
                        "once": "一次性", "hourly": "每小时", "daily": "每天",
                        "weekly": "每周", "realtime": "实时",
                    },
                    "status": {
                        "idle": "空闲", "running": "运行中",
                        "success": "成功", "failed": "失败",
                    },
                },
            }
        },
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(
        unique=True,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    name: str = Field(
        index=True,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    data_source_id: int = Field(
        foreign_key="data_source.id",
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    dataset_id: int = Field(
        foreign_key="dataset.id",
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    frequency: SyncFrequency = Field(default=SyncFrequency.DAILY)
    is_enabled: bool = Field(default=True)
    status: SyncTaskStatus = Field(
        default=SyncTaskStatus.IDLE,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    last_run_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    # 同步参数:增量字段、过滤条件等
    sync_config: Optional[dict] = Field(
        default=None,
        sa_column=Column(
            JSON, nullable=True,
            info={"site_props": {"component": "json"}},
        ),
    )
    description: Optional[str] = None
