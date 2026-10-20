from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel


class FieldDataType(str, Enum):
    STRING = "string"
    INT = "int"
    BIGINT = "bigint"
    DECIMAL = "decimal"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    JSON = "json"


class DatasetField(SQLModel, table=True):
    __tablename__ = "dataset_field"

    __onesite__ = {
        "standalone": False,
        "translations": {
            "zh": {
                "name": "数据集字段",
                "fields": {
                    "dataset_id": "所属数据集",
                    "name": "字段名",
                    "data_type": "数据类型",
                    "is_primary_key": "主键",
                    "is_index": "索引",
                    "nullable": "可空",
                    "description": "说明",
                },
                "enums": {
                    "data_type": {
                        "string": "字符串", "int": "整数", "bigint": "大整数",
                        "decimal": "小数", "float": "浮点", "boolean": "布尔",
                        "date": "日期", "datetime": "日期时间", "json": "JSON",
                    },
                },
            }
        },
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    # embedded 反向编辑器:在 Dataset 详情页内嵌管理字段
    dataset_id: int = Field(
        foreign_key="dataset.id",
        sa_column_kwargs={"info": {"site_props": {
            "reverse": {"editor": "embedded", "on_remove": "delete"},
        }}},
    )
    name: str = Field(
        index=True,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    data_type: FieldDataType = Field(default=FieldDataType.STRING)
    is_primary_key: bool = Field(default=False)
    is_index: bool = Field(default=False)
    nullable: bool = Field(default=True)
    description: Optional[str] = None
