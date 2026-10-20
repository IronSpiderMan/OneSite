from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel
from app.models.user import User

# Shared properties
class UserBase(SQLModel):

    
    email: str
    

    
    full_name: Optional[str]
    

    
    avatar: Optional[str]
    

    
    is_active: bool
    

    
    role: str
    

    

    

    
    created_at: datetime
    

    
    updated_at: datetime
    

    


# Properties to receive via API on creation
class UserCreate(SQLModel):
    email: str
    password: str
    full_name: Optional[str] = None
    avatar: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    
    # Allow other fields if any

    

    

    

    

    
    role: str
    

    

    

    

    

    


# Properties to receive via API on update
class UserUpdate(SQLModel):
    email: Optional[str] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    avatar: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    
    # Allow other fields if any

    

    

    

    

    

    

    

    

    

    


class UserUpdateMe(SQLModel):
    """Current user updates their own profile.

    Excludes admin-only fields (role, is_active, is_superuser).
    Includes old_password for password change verification.
    """
    full_name: Optional[str] = None
    avatar: Optional[str] = None
    password: Optional[str] = None
    old_password: Optional[str] = None

    # Auto-include any additional updatable fields from the model

    

    

    

    

    

    

    

    

    

    


class UserRead(UserBase):
    id: int
