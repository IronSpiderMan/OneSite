from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from app.models.product import Product, ProductVariant



# Shared properties
class ProductBase(SQLModel):


    

    
    name: str
    
    

    
    status: str
    
    

    
    is_featured: bool
    
    

    
    category_id: Optional[int]
    
    

    
    variants: List[ProductVariant]
    
    

    
    meta_data: Dict[str, Any]
    
    

    
    created_at: datetime
    
    

    
    cover_image: Optional[str]
    
    

    
    manual_file: Optional[str]
    
    

    

    
    internal_note: str
    
    




# Properties to receive via API on creation
class ProductCreate(SQLModel):


    

    
    
    
    name: str
    
    
    
    

    
    
    
    status: str = 'draft'
    
    
    
    

    
    
    
    is_featured: bool = False
    
    
    
    

    
    
    
    category_id: Optional[int] = None
    
    
    
    

    
    
    
    variants: List[ProductVariant] = Field(default_factory=list)
    
    
    
    

    
    
    
    meta_data: Dict[str, Any] = Field(default_factory=dict)
    
    
    
    

    

    
    
    
    cover_image: Optional[str] = None
    
    
    
    

    
    
    
    manual_file: Optional[str] = None
    
    
    
    

    
    
    
    import_source: str = ''
    
    
    
    

    
    
    
    internal_note: str = ''
    
    
    
    


    
    tag_ids: Optional[List[int]] = []
    
    




# Properties to receive via API on update
class ProductUpdate(SQLModel):


    

    
    
    name: Optional[str] = None
    
    
    

    
    
    status: Optional[str] = None
    
    
    

    
    
    is_featured: Optional[bool] = None
    
    
    

    
    
    category_id: Optional[int] = None
    
    
    

    
    
    variants: Optional[List[ProductVariant]] = None
    
    
    

    
    
    meta_data: Optional[Dict[str, Any]] = None
    
    
    

    

    
    
    cover_image: Optional[str] = None
    
    
    

    
    
    manual_file: Optional[str] = None
    
    
    

    

    
    
    internal_note: Optional[str] = None
    
    
    


    
    tag_ids: Optional[List[int]] = None
    
    





class ProductRead(ProductBase):
    id: int

    category_id_label: Optional[str] = None


    # For now, we don't return m2m fields in Read schema by default to avoid N+1 queries
    # Frontend will fetch them separately if needed, or we can add them later
    pass







class ProductTagMeta(SQLModel):
    id: int
    label: str
    order: int


