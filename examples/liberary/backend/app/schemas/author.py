from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from app.models.author import Author



# Shared properties
class AuthorBase(SQLModel):


    

    
    name: str
    
    




# Properties to receive via API on creation
class AuthorCreate(SQLModel):


    

    
    
    
    name: str
    
    
    
    





# Properties to receive via API on update
class AuthorUpdate(SQLModel):


    

    
    
    name: Optional[str] = None
    
    
    






class AuthorRead(AuthorBase):
    id: int





