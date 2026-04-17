from typing import Optional
from enum import Enum
from sqlmodel import Field, SQLModel
from datetime import datetime

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    DEVELOPER = "developer"

class UserBase(SQLModel):
    email: str = Field(unique=True, index=True, sa_column_kwargs={"info": {"site_props": {"permissions": "rc"}}})
    full_name: Optional[str] = Field(default=None, sa_column_kwargs={"info": {"site_props": {"permissions": "rcu"}}})
    avatar: Optional[str] = Field(default="https://placehold.co/100?text=User", sa_column_kwargs={"info": {"site_props": {"permissions": "rcu", "component": "image"}}})
    is_active: bool = Field(default=True, sa_column_kwargs={"info": {"site_props": {"permissions": "r"}}})
    role: UserRole = Field(default=UserRole.USER, sa_column_kwargs={"info": {"site_props": {"permissions": "rc"}}})

class User(UserBase, table=True):
    __onesite__ = {
        "permissions": {
            "user": "r",  # User can access /me endpoint with read (update handled separately)
            "admin": "rcud",  # Admin can CRUD users, but cannot create developer role
            "developer": "rcud",  # Developer has full access
        },
        "special_me_permissions": "ru",  # Special: user can access /me with ru
        "translations": {
            "zh": {
                "name": "用户",
                "fields": {
                    "email": "邮箱",
                    "full_name": "姓名",
                    "avatar": "头像",
                    "is_active": "是否启用",
                    "is_superuser": "是否超管",
                    "role": "角色",
                    "created_at": "创建时间",
                    "updated_at": "更新时间",
                    "password": "密码"
                }
            }
        }
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str = Field(sa_column_kwargs={"info": {"site_props": {"permissions": ""}}}) # Hidden
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"info": {"site_props": {"permissions": "r"}}})
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow, "info": {"site_props": {"permissions": "r"}}})
