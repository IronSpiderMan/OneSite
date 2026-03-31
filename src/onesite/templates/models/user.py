from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime

class UserBase(SQLModel):
    email: str = Field(unique=True, index=True, sa_column_kwargs={"info": {"site_props": {"permissions": "rc"}}})
    full_name: Optional[str] = Field(default=None, sa_column_kwargs={"info": {"site_props": {"permissions": "rcu"}}})
    avatar: Optional[str] = Field(default="https://placehold.co/100?text=User", sa_column_kwargs={"info": {"site_props": {"permissions": "rcu", "component": "image"}}})
    is_active: bool = Field(default=True, sa_column_kwargs={"info": {"site_props": {"permissions": "r"}}})
    is_superuser: bool = Field(default=False, sa_column_kwargs={"info": {"site_props": {"permissions": "r"}}})

class User(UserBase, table=True):
    __onesite__ = {
        "translations": {
            "zh": {
                "name": "用户",
                "fields": {
                    "email": "邮箱",
                    "full_name": "姓名",
                    "avatar": "头像",
                    "is_active": "是否启用",
                    "is_superuser": "是否超管",
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
