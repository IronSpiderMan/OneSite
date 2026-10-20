from typing import Optional

from sqlmodel import Field, SQLModel


class AdminSettings(SQLModel, table=True):
    __onesite__ = {"is_singleton": True, "permissions": "admin"}

    id: Optional[int] = Field(default=None, primary_key=True)
    banner_text: str = Field(default="Welcome", sa_column_kwargs={"info": {"site_props": {"permissions": "u"}}})
    maintenance_mode: bool = Field(default=False, sa_column_kwargs={"info": {"site_props": {"permissions": "u"}}})
