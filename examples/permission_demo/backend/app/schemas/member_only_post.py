from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from app.models.member_only_post import MemberOnlyPost



# Shared properties
class MemberOnlyPostBase(SQLModel):


    

    
    title: str
    
    

    
    content: str
    
    

    
    member_level: str
    
    

    
    created_at: datetime
    
    




# Properties to receive via API on creation
class MemberOnlyPostCreate(SQLModel):


    

    
    
    
    title: str
    
    
    
    

    
    
    
    content: str = ''
    
    
    
    

    
    
    
    member_level: str = 'gold'
    
    
    
    

    





# Properties to receive via API on update
class MemberOnlyPostUpdate(SQLModel):


    

    
    
    title: Optional[str] = None
    
    
    

    
    
    content: Optional[str] = None
    
    
    

    
    
    member_level: Optional[str] = None
    
    
    

    






class MemberOnlyPostRead(MemberOnlyPostBase):
    id: int





