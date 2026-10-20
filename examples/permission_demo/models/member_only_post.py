"""
MemberOnlyPost: Dict-format permissions — users are read-only.

__onesite__.permissions uses dict format:
  {"user": "r", "admin": "rcu", "developer": "rcud"}

This means:
  - User role:   read-only  (can view posts, cannot create/update/delete)
  - Admin role:  read + create + update (cannot delete)
  - Developer:   full CRUD
  - The router will use min_role_for_read=USER (r is in user's perms)
  - Create endpoint requires ADMIN (c is not in user perms)
  - Update endpoint requires ADMIN (u is not in user perms)
  - Delete endpoint requires DEVELOPER (d is only in developer perms)
  - Menu visible to all roles (all have at least "r")
"""
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class MemberOnlyPost(SQLModel, table=True):
    __onesite__ = {
        "permissions": {
            "user": "r",
            "admin": "cru",
            "developer": "crud",
        },
        "translations": {
            "zh": {
                "name": "会员文章",
                "fields": {
                    "title": "标题",
                    "content": "内容",
                    "member_level": "会员等级",
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
    member_level: str = Field(default="gold")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"info": {"site_props": {"permissions": "r"}}},
    )
