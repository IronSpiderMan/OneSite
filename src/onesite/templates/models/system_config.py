from typing import Optional
from datetime import time
from sqlmodel import Field, SQLModel

class SystemConfig(SQLModel, table=True):
    __onesite__ = {"config_role": "system", "permissions": "admin", "is_singleton": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Global System Name
    site_name: str = Field(default="OneSite Admin")
    
    # Shift times
    day_shift_start_at: time = Field(default="08:00:00")
    day_shift_end_at: time = Field(default="17:00:00")
    night_shift_start_at: time = Field(default="17:00:00")
    night_shift_end_at: time = Field(default="23:59:59")
    
    allow_registration: bool = Field(default=True)

