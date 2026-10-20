from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from app.models.category import Category



# Shared properties
class CategoryBase(SQLModel):


    

    
    name: str
    
    

    
    description: Optional[str]
    
    




# Properties to receive via API on creation
class CategoryCreate(SQLModel):


    

    
    
    
    name: str
    
    
    
    

    
    
    
    description: Optional[str] = None
    
    
    
    





# Properties to receive via API on update
class CategoryUpdate(SQLModel):


    

    
    
    name: Optional[str] = None
    
    
    

    
    
    description: Optional[str] = None
    
    
    






class CategoryRead(CategoryBase):
    id: int





