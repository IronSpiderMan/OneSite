from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel, Relationship


class ProductStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ProductVariant(BaseModel):
    sku: str
    price: float
    stock: int


class Product(SQLModel, table=True):
    __onesite__ = {
        "importable": True,
        "exportable": True,
        "import_key": "name"
    }
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}})
    status: ProductStatus = Field(default=ProductStatus.DRAFT, sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}})
    is_featured: bool = Field(default=False, sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}})

    category_id: Optional[int] = Field(
        default=None, 
        foreign_key="category.id",
        sa_column_kwargs={"info": {"site_props": {"reverse_display": True}}}
    )
    category: Optional["Category"] = Relationship(back_populates="products")

    variants: List[ProductVariant] = Field(default_factory=list, sa_column=Column(JSON))
    meta_data: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"info": {"site_props": {"permissions": "r", "is_search_field": True}}},
    )

    cover_image: Optional[str] = Field(
        default=None,
        sa_column_kwargs={"info": {"site_props": {"component": "image"}}},
    )

    manual_file: Optional[str] = Field(
        default=None,
        sa_column_kwargs={"info": {"site_props": {"component": "file", "allow_download": False}}},
    )

    import_source: str = Field(
        default="",
        sa_column_kwargs={"info": {"site_props": {"permissions": "c", "create_optional": True}}},
    )

    internal_note: str = Field(
        default="",
        sa_column_kwargs={"info": {"site_props": {"permissions": "cru", "update_optional": True}}},
    )
