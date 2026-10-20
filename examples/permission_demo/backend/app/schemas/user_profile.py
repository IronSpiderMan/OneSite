from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from app.models.user_profile import UserProfile



# Shared properties
class UserProfileBase(SQLModel):


    

    
    display_name: str
    
    

    
    avatar: Optional[str]
    
    

    
    bio: str
    
    

    
    phone: str
    
    

    
    ssn: str
    
    

    
    internal_note: str
    
    

    
    loyalty_points: int
    
    

    
    id_document: Optional[str]
    
    

    
    created_at: datetime
    
    




# Properties to receive via API on creation
class UserProfileCreate(SQLModel):


    

    
    
    
    display_name: str
    
    
    
    

    
    
    
    avatar: Optional[str] = None
    
    
    
    

    
    
    
    bio: str = ''
    
    
    
    

    
    
    
    phone: str = ''
    
    
    
    

    

    
    
    
    internal_note: str = ''
    
    
    
    

    
    
    
    loyalty_points: int = 0
    
    
    
    

    
    
    
    id_document: Optional[str] = None
    
    
    
    

    





# Properties to receive via API on update
class UserProfileUpdate(SQLModel):


    

    
    
    display_name: Optional[str] = None
    
    
    

    
    
    avatar: Optional[str] = None
    
    
    

    
    
    bio: Optional[str] = None
    
    
    

    
    
    phone: Optional[str] = None
    
    
    

    

    
    
    internal_note: Optional[str] = None
    
    
    

    
    
    loyalty_points: Optional[int] = None
    
    
    

    
    
    id_document: Optional[str] = None
    
    
    

    






class UserProfileRead(UserProfileBase):
    id: int





