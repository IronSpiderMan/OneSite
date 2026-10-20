from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"


class DataService(SQLModel, table=True):
    __tablename__ = "data_service"

    __onesite__ = {
        "icon": "Plug",
        "importable": True,
        "exportable": True,
        "import_key": "code",
        "actions": {
            "toggle_enabled": {"toggle": "is_enabled", "permissions": "du"},
        },
        "translations": {
            "zh": {
                "name": "数据服务",
                "fields": {
                    "code": "服务编码",
                    "name": "服务名称",
                    "dataset_id": "关联数据集",
                    "method": "请求方法",
                    "path": "接口路径",
                    "is_enabled": "是否启用",
                    "description": "描述",
                },
                "enums": {"method": {"GET": "GET", "POST": "POST"}},
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
    dataset_id: int = Field(
        foreign_key="dataset.id",
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    method: HttpMethod = Field(default=HttpMethod.GET)
    path: str = Field(default="/api/data")
    is_enabled: bool = Field(default=True)
    description: Optional[str] = None
