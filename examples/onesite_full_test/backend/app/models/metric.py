from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Metric(SQLModel, table=True):
    __onesite__ = {"auto_refresh": True, "refresh_interval": 2000}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}})
    value: float = 0.0
    recorded_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )

