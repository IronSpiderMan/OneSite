from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from app.models.premium_content import PremiumContent



# Shared properties
class PremiumContentBase(SQLModel):


    

    
    title: str
    
    

    
    body: str
    
    

    
    price: float
    
    

    
    created_at: datetime
    
    




# Properties to receive via API on creation
class PremiumContentCreate(SQLModel):


    

    
    
    
    title: str
    
    
    
    

    
    
    
    body: str = ''
    
    
    
    

    
    
    
    price: float = 0.0
    
    
    
    

    





# Properties to receive via API on update
class PremiumContentUpdate(SQLModel):


    

    
    
    title: Optional[str] = None
    
    
    

    
    
    body: Optional[str] = None
    
    
    

    
    
    price: Optional[float] = None
    
    
    

    






class PremiumContentRead(PremiumContentBase):
    id: int





