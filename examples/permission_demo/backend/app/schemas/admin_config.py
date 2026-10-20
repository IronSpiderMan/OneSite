from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel
from app.models.admin_config import AdminConfig

# Shared properties
class AdminConfigBase(SQLModel):


    

    
    site_name: str
    
    

    
    max_upload_size: int
    
    

    
    enable_registration: bool
    
    




# Properties to receive via API on update
class AdminConfigUpdate(SQLModel):


    

    
    site_name: str = None
    
    

    
    max_upload_size: int = None
    
    

    
    enable_registration: bool = None
    
    



class AdminConfigRead(AdminConfigBase):
    id: int