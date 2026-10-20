from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from app.models.subject import Subject



# Shared properties
class SubjectBase(SQLModel):


    

    
    title: str
    
    




# Properties to receive via API on creation
class SubjectCreate(SQLModel):


    

    
    
    
    title: str
    
    
    
    





# Properties to receive via API on update
class SubjectUpdate(SQLModel):


    

    
    
    title: Optional[str] = None
    
    
    






class SubjectRead(SubjectBase):
    id: int





