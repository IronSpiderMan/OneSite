"""
AdminConfig: String-format "admin" permission — admin-only singleton.

__onesite__.permissions = "admin" means:
  - Only admin+ roles can access (admin="rcud", developer="rcud")
  - User role has no access (user="")
  - This is a singleton model (only one record)
  - The router requires ADMIN role
  - Not visible in user menus
  - All endpoints require ADMIN or higher
"""
from typing import Optional
from sqlmodel import Field, SQLModel


class AdminConfig(SQLModel, table=True):
    __onesite__ = {
        "is_singleton": True,
        "permissions": {
            "user": "",
            "admin": "crud",
            "developer": "crud",
        },
        "visible": ["admin", "developer"],
        "translations": {
            "zh": {
                "name": "管理员配置",
                "fields": {
                    "site_name": "站点名称",
                    "max_upload_size": "最大上传大小",
                    "enable_registration": "允许注册",
                }
            }
        }
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    site_name: str = Field(default="My Site")
    max_upload_size: int = Field(default=10)
    enable_registration: bool = Field(default=True)
