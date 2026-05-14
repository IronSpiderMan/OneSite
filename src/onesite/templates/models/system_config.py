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
    }

    id: Optional[int] = Field(default=None, primary_key=True)

    # Global System Name
    site_name: str = Field(default="OneSite Admin")

    allow_registration: bool = Field(default=True)
