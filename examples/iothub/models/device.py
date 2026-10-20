from typing import Optional
from sqlmodel import Field, SQLModel
from enum import Enum

class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"

class Device(SQLModel, table=True):
    __tablename__ = "device"

    __onesite__ = {
        "translations": {
            "zh": {
                "name": "设备",
                "fields": {
                    "name": "设备名称",
                    "device_key": "设备编号",
                    "status": "状态",
                    "data_model_id": "所属模型"
                }
            }
        }
    }
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}})
    device_key: str = Field(unique=True, sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}})
    status: DeviceStatus = Field(default=DeviceStatus.OFFLINE, sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}})
    
    # 外键关联到 DataModel
    data_model_id: Optional[int] = Field(
        default=None, 
        foreign_key="data_model.id",
        sa_column_kwargs={"info": {"site_props": {"reverse_display": True}}}
    )
