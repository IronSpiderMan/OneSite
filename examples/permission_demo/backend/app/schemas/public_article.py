from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from app.models.public_article import PublicArticle



# Shared properties
class PublicArticleBase(SQLModel):


    

    
    title: str
    
    

    
    content: str
    
    

    
    is_published: bool
    
    

    
    created_at: datetime
    
    




# Properties to receive via API on creation
class PublicArticleCreate(SQLModel):


    

    
    
    
    title: str
    
    
    
    

    
    
    
    content: str = ''
    
    
    
    

    
    
    
    is_published: bool = False
    
    
    
    

    





# Properties to receive via API on update
class PublicArticleUpdate(SQLModel):


    

    
    
    title: Optional[str] = None
    
    
    

    
    
    content: Optional[str] = None
    
    
    

    
    
    is_published: Optional[bool] = None
    
    
    

    






class PublicArticleRead(PublicArticleBase):
    id: int





