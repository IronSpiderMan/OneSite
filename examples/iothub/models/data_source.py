from typing import Optional
from sqlmodel import Field, SQLModel

class DataSource(SQLModel, table=True):
    __tablename__ = "data_source"

    __onesite__ = {
        "translations": {
            "zh": {
                "name": "数据源",
                "fields": {
                    "name": "数据源名称",
                    "type": "数据源类型",
                    "host": "主机地址",
                    "port": "端口号",
                    "description": "描述"
                }
            }
        }
    }
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}})
    type: str = Field(sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}})
    host: str
    port: int
    description: Optional[str] = None
