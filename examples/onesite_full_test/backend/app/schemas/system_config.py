from typing import Optional, List, Dict, Any
from datetime import datetime, time
from sqlmodel import SQLModel
from app.models.system_config import SystemConfig

# Shared properties
class SystemConfigBase(SQLModel):


    

    
    site_name: str
    
    

    
    day_shift_start_at: time
    
    

    
    day_shift_end_at: time
    
    

    
    night_shift_start_at: time
    
    

    
    night_shift_end_at: time
    
    

    
    allow_registration: bool
    
    




# Properties to receive via API on update
class SystemConfigUpdate(SQLModel):


    

    
    site_name: str = None
    
    

    
    day_shift_start_at: time = None
    
    

    
    day_shift_end_at: time = None
    
    

    
    night_shift_start_at: time = None
    
    

    
    night_shift_end_at: time = None
    
    

    
    allow_registration: bool = None
    
    



class SystemConfigRead(SystemConfigBase):
    id: int