from enum import Enum
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


class DatasetType(str, Enum):
    DIMENSION = "dimension"   # 维表
    FACT = "fact"             # 事实表
    WIDE = "wide"             # 宽表
    VIEW = "view"             # 视图/汇总


class DatasetStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class Dataset(SQLModel, table=True):
    __tablename__ = "dataset"

    __onesite__ = {
        "icon": "Table2",
        "importable": True,
        "exportable": True,
        "import_key": "code",
        "refresh_interval": 30,
        "edit_mode": "drawer",
        "actions": {
            "toggle_published": {
                "toggle": "is_published",
                "permissions": "du",
            },
        },
        "translations": {
            "zh": {
                "name": "数据集",
                "fields": {
                    "name": "数据集名称",
                    "code": "数据集编码",
                    "type": "数据集类型",
                    "data_source_id": "所属数据源",
                    "table_name": "物理表名",
                    "owner": "负责人",
                    "is_published": "是否发布",
                    "status": "状态",
                    "row_count": "行数",
                    "description": "描述",
                },
                "enums": {
                    "type": {
                        "dimension": "维表", "fact": "事实表",
                        "wide": "宽表", "view": "视图/汇总",
                    },
                    "status": {"draft": "草稿", "published": "已发布", "deprecated": "已下线"},
                },
            }
        },
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(
        unique=True, index=True,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    code: str = Field(
        unique=True,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    type: DatasetType = Field(
        default=DatasetType.FACT,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    data_source_id: int = Field(
        foreign_key="data_source.id",
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    table_name: str
    owner: Optional[str] = None
    is_published: bool = Field(default=False)
    status: DatasetStatus = Field(
        default=DatasetStatus.DRAFT,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    row_count: Optional[int] = None
    last_synced_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    description: Optional[str] = None
