from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from app.models.metric import Metric



# Shared properties
class MetricBase(SQLModel):


    

    
    name: str
    
    

    
    value: float
    
    

    
    recorded_at: datetime
    
    




# Properties to receive via API on creation
class MetricCreate(SQLModel):


    

    
    
    
    name: str
    
    
    
    

    
    
    
    value: float = 0.0
    
    
    
    

    
    
    
    recorded_at: datetime = None
    
    
    
    





# Properties to receive via API on update
class MetricUpdate(SQLModel):


    

    
    
    name: Optional[str] = None
    
    
    

    
    
    value: Optional[float] = None
    
    
    

    
    
    recorded_at: Optional[datetime] = None
    
    
    






class MetricRead(MetricBase):
    id: int





