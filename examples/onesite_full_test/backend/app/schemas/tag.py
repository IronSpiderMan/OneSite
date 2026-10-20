from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from app.models.tag import Tag



# Shared properties
class TagBase(SQLModel):


    

    
    name: str
    
    




# Properties to receive via API on creation
class TagCreate(SQLModel):


    

    
    
    
    name: str
    
    
    
    





# Properties to receive via API on update
class TagUpdate(SQLModel):


    

    
    
    name: Optional[str] = None
    
    
    






class TagRead(TagBase):
    id: int





