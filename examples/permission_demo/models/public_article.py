"""
PublicArticle: Default "rcud" permissions for all roles.

No __onesite__.permissions is specified, so the system defaults
to granting all roles (user, admin, developer) full "rcud" access.
This means:
  - All users can read/create/update/delete articles
  - The model appears in all role menus
  - No role-based restrictions on any endpoint
"""
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class PublicArticle(SQLModel, table=True):
    __onesite__ = {
        "translations": {
            "zh": {
                "name": "公开文章",
                "fields": {
                    "title": "标题",
                    "content": "内容",
                    "is_published": "是否发布",
                    "created_at": "创建时间",
                }
            }
        }
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}}
    )
    content: str = Field(default="")
    is_published: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"info": {"site_props": {"permissions": "r"}}},
    )
