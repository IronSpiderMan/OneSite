from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel
from app.models.secret_config import SecretConfig

# Shared properties
class SecretConfigBase(SQLModel):


    

    
    api_key: str
    
    

    
    internal_url: str
    
    

    
    debug_mode: bool
    
    




# Properties to receive via API on update
class SecretConfigUpdate(SQLModel):


    

    
    api_key: str = None
    
    

    
    internal_url: str = None
    
    

    
    debug_mode: bool = None
    
    



class SecretConfigRead(SecretConfigBase):
    id: int