from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from app.models.data_source import DataSource



# Shared properties
class DataSourceBase(SQLModel):


    

    
    name: str
    
    

    
    type: str
    
    

    
    host: str
    
    

    
    port: int
    
    

    
    description: Optional[str]
    
    




# Properties to receive via API on creation
class DataSourceCreate(SQLModel):


    

    
    
    
    name: str
    
    
    
    

    
    
    
    type: str
    
    
    
    

    
    
    
    host: str
    
    
    
    

    
    
    
    port: int
    
    
    
    

    
    
    
    description: Optional[str] = None
    
    
    
    




# Properties to receive via API on update
class DataSourceUpdate(SQLModel):


    

    
    
    name: Optional[str] = None
    
    
    

    
    
    type: Optional[str] = None
    
    
    

    
    
    host: Optional[str] = None
    
    
    

    
    
    port: Optional[int] = None
    
    
    

    
    
    description: Optional[str] = None
    
    
    





class DataSourceRead(DataSourceBase):
    id: int





