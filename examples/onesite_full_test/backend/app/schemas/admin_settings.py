from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel
from app.models.admin_settings import AdminSettings

# Shared properties
class AdminSettingsBase(SQLModel):


    

    

    


    pass



# Properties to receive via API on update
class AdminSettingsUpdate(SQLModel):


    

    
    banner_text: str = None
    
    

    
    maintenance_mode: bool = None
    
    



class AdminSettingsRead(AdminSettingsBase):
    id: int