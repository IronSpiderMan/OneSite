"""
SecretConfig: String-format "developer-rcu" — developer-only.

__onesite__.permissions = "developer-rcu" means:
  - Only developer role can access (developer="rcu")
  - Admin has no access (admin="")
  - User has no access (user="")
  - The router requires DEVELOPER role
  - Not visible in user or admin menus
  - Only developer can read/create/update (no delete)

Note: String format "developer-rcu" gets parsed as:
  - user="" (level 0 < developer's level 2)
  - admin="" (level 1 < developer's level 2)
  - developer="rcu" (level 2 >= developer's level 2)
"""
from typing import Optional
from sqlmodel import Field, SQLModel


class SecretConfig(SQLModel, table=True):
    __onesite__ = {
        "is_singleton": True,
        "permissions": {
            "user": "",
            "admin": "",
            "developer": "cru",
        },
        "visible": ["developer"],
        "translations": {
            "zh": {
                "name": "秘密配置",
                "fields": {
                    "api_key": "API密钥",
                    "internal_url": "内部URL",
                    "debug_mode": "调试模式",
                }
            }
        }
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    api_key: str = Field(default="")
    internal_url: str = Field(default="")
    debug_mode: bool = Field(default=False)
