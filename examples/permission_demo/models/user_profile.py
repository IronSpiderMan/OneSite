"""
UserProfile: Complex mixed permissions with field-level control.

Model-level permissions (dict format):
  {"user": "rcu", "admin": "rcu", "developer": "rcud"}
  - User can read/create/update but NOT delete
  - Admin can read/create/update but NOT delete
  - Developer has full CRUD

Field-level permissions (various formats):
  - avatar:       dict format {"user": "rcu", "admin": "rcu", "developer": "rcu"} + image component
  - bio:          string format "rcu" (default — all can read/create/update)
  - phone:        string format "admin-rcu" (only admin+ can see/edit)
  - ssn:          string format "developer-r" (only developer can read)
  - internal_note: dict format {"admin": "u", "developer": "rcu"} (admin can only update)
  - loyalty_points: dict format {"user": "r", "developer": "rcu"} (user read-only for this field)
  - id_document:  string format "developer-rcu" + file component
"""
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class UserProfile(SQLModel, table=True):
    __onesite__ = {
        "permissions": {
            "user": "cru",
            "admin": "cru",
            "developer": "crud",
        },
        "translations": {
            "zh": {
                "name": "用户资料",
                "fields": {
                    "display_name": "显示名称",
                    "bio": "简介",
                    "avatar": "头像",
                    "phone": "电话",
                    "ssn": "社会保障号",
                    "internal_note": "内部备注",
                    "loyalty_points": "积分",
                    "created_at": "创建时间",
                }
            }
        }
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    display_name: str = Field(
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}}
    )

    # Field with dict-format permissions + image component
    avatar: Optional[str] = Field(
        default=None,
        sa_column_kwargs={
            "info": {
                "site_props": {
                    "permissions": {"user": "rcu", "admin": "rcu", "developer": "rcu"},
                    "component": "image",
                }
            }
        },
    )

    # Field with default string "rcu" permissions
    bio: str = Field(
        default="",
        sa_column_kwargs={"info": {"site_props": {"permissions": "rcu"}}},
    )

    # Field with "admin-rcu" string — only admin+ can read/create/update
    phone: str = Field(
        default="",
        sa_column_kwargs={"info": {"site_props": {"permissions": "admin-rcu"}}},
    )

    # Field with "developer-r" string — only developer can read (never write)
    ssn: str = Field(
        default="",
        sa_column_kwargs={"info": {"site_props": {"permissions": "developer-r"}}},
    )

    # Field with dict-format permissions — admin can only update, developer full
    internal_note: str = Field(
        default="",
        sa_column_kwargs={
            "info": {
                "site_props": {
                    "permissions": {"admin": "u", "developer": "rcu"},
                }
            }
        },
    )

    # Field with dict-format — user read-only, developer full
    loyalty_points: int = Field(
        default=0,
        sa_column_kwargs={
            "info": {
                "site_props": {
                    "permissions": {"user": "r", "developer": "rcu"},
                }
            }
        },
    )

    # File field with developer-only access
    id_document: Optional[str] = Field(
        default=None,
        sa_column_kwargs={
            "info": {
                "site_props": {
                    "permissions": "developer-rcu",
                    "component": "file",
                }
            }
        },
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"info": {"site_props": {"permissions": "r"}}},
    )
