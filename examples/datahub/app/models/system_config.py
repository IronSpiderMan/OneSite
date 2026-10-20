from typing import Optional
from sqlmodel import Field, SQLModel

class SystemConfig(SQLModel, table=True):
    __onesite__ = {
        "permissions": {
            "user": "r",
            "admin": "crud",
            "developer": "crud",
        },
        "visible": ["admin", "developer", "user"],
        "groups": [
            {"key": "default"},
            {"key": "announcement", "en": "Announcement", "zh": "公告"},
        ],
    }

    id: Optional[int] = Field(default=None, primary_key=True)

    # Global System Name
    site_name: str = Field(default="OneSite Admin")

    logo: Optional[str] = Field(
        default=None,
        sa_column_kwargs={"info": {"site_props": {
            "permissions": {"user": "r", "admin": "cru", "developer": "cru"},
            "component": "image",
        }}},
    )

    allow_registration: bool = Field(default=True)

    # Dashboard Announcement (markdown supported)
    announcement_content: Optional[str] = Field(
        default=None,
        sa_column_kwargs={"info": {"site_props": {
            "permissions": {"user": "r", "admin": "cru", "developer": "cru"},
            "component": "textarea",
            "group": "announcement",
        }}},
    )
