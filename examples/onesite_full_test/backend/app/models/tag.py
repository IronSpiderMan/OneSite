from typing import Optional

from sqlmodel import Field, SQLModel


class Tag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(
        unique=True,
        index=True,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
