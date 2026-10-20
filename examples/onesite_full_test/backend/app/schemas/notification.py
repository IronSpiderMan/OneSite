from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from app.models.notification import Notification



# Shared properties
class NotificationBase(SQLModel):


    

    
    title: str
    
    

    
    summary: str
    
    

    
    content: str
    
    

    
    created_at: datetime
    
    

    
    is_read: bool
    
    

    
    user_id: int
    
    




# Properties to receive via API on creation
class NotificationCreate(SQLModel):


    

    
    
    
    title: str = ''
    
    
    
    

    
    
    
    summary: str = ''
    
    
    
    

    
    
    
    content: str = ''
    
    
    
    

    

    
    
    
    is_read: bool = False
    
    
    
    

    
    
    
    # user_id is optional in create - None means broadcast to all users
    user_id: Optional[int] = None
    
    
    
    





# Properties to receive via API on update
class NotificationUpdate(SQLModel):


    

    
    
    title: Optional[str] = None
    
    
    

    
    
    summary: Optional[str] = None
    
    
    

    
    
    content: Optional[str] = None
    
    
    

    

    
    
    is_read: Optional[bool] = None
    
    
    

    
    
    user_id: Optional[int] = None
    
    
    






class NotificationRead(NotificationBase):
    id: int

    user_id_label: Optional[str] = None




class NotificationSend(SQLModel):
    title: str
    content: str
    summary: Optional[str] = None
    user_id: Optional[int] = None
    broadcast: bool = False


