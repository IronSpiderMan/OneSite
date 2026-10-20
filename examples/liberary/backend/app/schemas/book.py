from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from app.models.book import Book



# Shared properties
class BookBase(SQLModel):


    

    
    title: str
    
    

    
    published_at: datetime
    
    

    
    author_id: int
    
    




# Properties to receive via API on creation
class BookCreate(SQLModel):


    

    
    
    
    title: str
    
    
    
    

    

    
    
    
    author_id: int
    
    
    
    


    
    subject_ids: Optional[List[int]] = []
    
    




# Properties to receive via API on update
class BookUpdate(SQLModel):


    

    
    
    title: Optional[str] = None
    
    
    

    

    
    
    author_id: Optional[int] = None
    
    
    


    
    subject_ids: Optional[List[int]] = None
    
    





class BookRead(BookBase):
    id: int

    author_id_label: Optional[str] = None


    # For now, we don't return m2m fields in Read schema by default to avoid N+1 queries
    # Frontend will fetch them separately if needed, or we can add them later
    pass








