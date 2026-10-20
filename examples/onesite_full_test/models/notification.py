from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Notification(SQLModel, table=True):
    __onesite__ = {"is_notification_table": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(default="")
    summary: str = Field(default="")
    content: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"info": {"site_props": {"permissions": "r"}}})
    is_read: bool = Field(default=False)
    user_id: int = Field(foreign_key="user.id")

