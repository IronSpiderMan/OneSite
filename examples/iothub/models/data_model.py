from typing import Optional
from sqlmodel import Field, SQLModel

class DataModel(SQLModel, table=True):
    __tablename__ = "data_model"

    __onesite__ = {
        "translations": {
            "zh": {
                "name": "数据模型",
                "fields": {
                    "name": "模型名称",
                    "identifier": "标识符",
                    "version": "版本",
                    "data_source_id": "关联数据源"
                }
            }
        }
    }
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}})
    identifier: str = Field(unique=True, sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}})
    version: str = Field(default="1.0")
    
    # 外键关联到 DataSource
    data_source_id: Optional[int] = Field(
        default=None, 
        foreign_key="data_source.id",
        sa_column_kwargs={"info": {"site_props": {"reverse_display": True}}}
    )
