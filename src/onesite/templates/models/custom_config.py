from enum import Enum
from sqlmodel import Field, SQLModel

class LanguageEnum(str, Enum):
    EN = "en"
    ZH = "zh"

class TimezoneEnum(str, Enum):
    UTC = "UTC"
    ASIA_SHANGHAI = "Asia/Shanghai"

class ThemeStyleEnum(str, Enum):
    NORMAL = "normal"
    INDUSTRIAL = "industrial"
    NEURON = "neuron"

class ThemeModeEnum(str, Enum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"

class CustomConfig(SQLModel):
    __onesite__ = {"frontend_only": True}

    # Local Settings (Stored only in browser localStorage)
    language: LanguageEnum = Field(
        default=LanguageEnum.EN
    )

    timezone: TimezoneEnum = Field(
        default=TimezoneEnum.UTC
    )

    theme_style: ThemeStyleEnum = Field(
        default=ThemeStyleEnum.NORMAL
    )

    theme_mode: ThemeModeEnum = Field(
        default=ThemeModeEnum.SYSTEM
    )
