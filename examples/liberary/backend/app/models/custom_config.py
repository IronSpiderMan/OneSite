from enum import Enum
from sqlmodel import Field, SQLModel

class LanguageEnum(str, Enum):
    EN = "en"
    ZH = "zh"

class TimezoneEnum(str, Enum):
    UTC = "UTC"
    ASIA_SHANGHAI = "Asia/Shanghai"

class ThemeEnum(str, Enum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"
    IOTHUB = "iothub"

class CustomConfig(SQLModel):
    # CustomConfig is auto-detected as frontend_only by name

    # Local Settings (Stored only in browser localStorage)
    language: LanguageEnum = Field(
        default=LanguageEnum.EN
    )
    
    timezone: TimezoneEnum = Field(
        default=TimezoneEnum.UTC
    )

    theme: ThemeEnum = Field(
        default=ThemeEnum.SYSTEM
    )
