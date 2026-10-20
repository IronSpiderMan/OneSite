from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from app.models.device import Device



# Shared properties
class DeviceBase(SQLModel):


    

    
    name: str
    
    

    
    device_key: str
    
    

    
    status: str
    
    

    
    data_model_id: Optional[int]
    
    




# Properties to receive via API on creation
class DeviceCreate(SQLModel):


    

    
    
    
    name: str
    
    
    
    

    
    
    
    device_key: str
    
    
    
    

    
    
    
    status: str = 'offline'
    
    
    
    

    
    
    
    data_model_id: Optional[int] = None
    
    
    
    




# Properties to receive via API on update
class DeviceUpdate(SQLModel):


    

    
    
    name: Optional[str] = None
    
    
    

    
    
    device_key: Optional[str] = None
    
    
    

    
    
    status: Optional[str] = None
    
    
    

    
    
    data_model_id: Optional[int] = None
    
    
    





class DeviceRead(DeviceBase):
    id: int

    data_model_id_label: Optional[str] = None





