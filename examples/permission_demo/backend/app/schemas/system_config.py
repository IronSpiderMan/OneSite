from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel
from app.models.system_config import SystemConfig

# Shared properties
class SystemConfigBase(SQLModel):


    

    
    site_name: str
    
    

    
    allow_registration: bool
    
    




# Properties to receive via API on update
class SystemConfigUpdate(SQLModel):


    

    
    site_name: str = None
    
    

    
    allow_registration: bool = None
    
    



class SystemConfigRead(SystemConfigBase):
    id: int