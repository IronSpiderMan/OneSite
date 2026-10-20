"""
PremiumContent: String-format "admin-rcud" — admin+ full access.

__onesite__.permissions = "admin-rcud" means:
  - No access for user role (user="")
  - Admin gets "rcud" (full access)
  - Developer gets "rcud" (full access, inherits from admin level)
  - The router requires ADMIN role
  - Only visible in admin and developer menus
  - All CRUD operations require ADMIN+
"""
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class PremiumContent(SQLModel, table=True):
    __onesite__ = {
        "permissions": {
            "user": "",
            "admin": "crud",
            "developer": "crud",
        },
        "visible": ["admin", "developer"],
        "translations": {
            "zh": {
                "name": "高级内容",
                "fields": {
                    "title": "标题",
                    "body": "内容",
                    "price": "价格",
                    "created_at": "创建时间",
                }
            }
        }
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}}
    )
    body: str = Field(default="")
    price: float = Field(default=0.0)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"info": {"site_props": {"permissions": "r"}}},
    )
