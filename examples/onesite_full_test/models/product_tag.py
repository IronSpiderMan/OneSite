from typing import Optional

from sqlmodel import Field, SQLModel


class ProductTag(SQLModel, table=True):
    __onesite__ = {"is_link_table": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id")
    tag_id: int = Field(foreign_key="tag.id")
    order: int = Field(default=1)
