from enum import Enum
from typing import Optional
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class DataSourceType(str, Enum):
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    ORACLE = "oracle"
    KAFKA = "kafka"
    API = "api"
    FILE = "file"


class DataSourceStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class DataSource(SQLModel, table=True):
    __tablename__ = "data_source"

    __onesite__ = {
        "icon": "Database",
        "importable": True,
        "exportable": True,
        "import_key": "name",
        "translations": {
            "zh": {
                "name": "数据源",
                "fields": {
                    "name": "数据源名称",
                    "source_key": "数据源标识",
                    "type": "数据源类型",
                    "host": "主机地址",
                    "port": "端口号",
                    "database_name": "库名",
                    "status": "状态",
                    "description": "描述",
                },
                "enums": {
                    "type": {
                        "mysql": "MySQL", "postgresql": "PostgreSQL",
                        "oracle": "Oracle", "kafka": "Kafka",
                        "api": "接口", "file": "文件",
                    },
                    "status": {"active": "正常", "inactive": "停用", "error": "异常"},
                },
            }
        },
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(
        unique=True, index=True,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    source_key: str = Field(
        unique=True,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    type: DataSourceType = Field(
        default=DataSourceType.MYSQL,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    host: str
    port: int = 3306
    database_name: Optional[str] = None
    # 连接凭据/附加配置,仅 developer/admin 可读写
    connection_config: Optional[dict] = Field(
        default=None,
        sa_column=Column(
            JSON, nullable=True,
            info={"site_props": {
                "permissions": {"user": "r", "admin": "cru", "developer": "cru"},
                "component": "json",
            }},
        ),
    )
    status: DataSourceStatus = Field(
        default=DataSourceStatus.ACTIVE,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    description: Optional[str] = None
