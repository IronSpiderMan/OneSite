from enum import Enum
from sqlmodel import Field, SQLModel

class LanguageEnum(str, Enum):
    EN = "en"
    ZH = "zh"

class TimezoneEnum(str, Enum):
    UTC = "UTC"
    ASIA_SHANGHAI = "Asia/Shanghai"

class CustomConfig(SQLModel):
    __onesite__ = {"config_role": "custom", "frontend_only": True}

    # Local Settings (Stored only in browser localStorage)
    language: LanguageEnum = Field(
        default=LanguageEnum.EN
    )
    
    timezone: TimezoneEnum = Field(
        default=TimezoneEnum.UTC
    )
