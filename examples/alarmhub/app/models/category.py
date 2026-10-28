"""Alarm categories, following the AlarmHub organization."""

from typing import Optional
from onesite.config import OneSiteConfig
from sqlmodel import Field, SQLModel


class Category(SQLModel, table=True):
    __onesite__ = OneSiteConfig(
        icon="Tags",
        page_edit=True,
        permissions={"user": "r", "admin": "r", "developer": "crud"},
        translations={"zh": {"name": "告警分类", "fields": {"title": "名称"}}},
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(unique=True, index=True)
