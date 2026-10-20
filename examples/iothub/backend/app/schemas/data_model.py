from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from app.models.data_model import DataModel



# Shared properties
class DataModelBase(SQLModel):


    

    
    name: str
    
    

    
    identifier: str
    
    

    
    version: str
    
    

    
    data_source_id: Optional[int]
    
    




# Properties to receive via API on creation
class DataModelCreate(SQLModel):


    

    
    
    
    name: str
    
    
    
    

    
    
    
    identifier: str
    
    
    
    

    
    
    
    version: str = '1.0'
    
    
    
    

    
    
    
    data_source_id: Optional[int] = None
    
    
    
    




# Properties to receive via API on update
class DataModelUpdate(SQLModel):


    

    
    
    name: Optional[str] = None
    
    
    

    
    
    identifier: Optional[str] = None
    
    
    

    
    
    version: Optional[str] = None
    
    
    

    
    
    data_source_id: Optional[int] = None
    
    
    





class DataModelRead(DataModelBase):
    id: int

    data_source_id_label: Optional[str] = None





