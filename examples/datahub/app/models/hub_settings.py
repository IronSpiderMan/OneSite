from typing import Optional
from sqlmodel import Field, SQLModel


class HubSettings(SQLModel, table=True):
    __tablename__ = "hub_settings"

    __onesite__ = {
        "is_singleton": True,
        "visible": ["admin", "developer"],
        "translations": {
            "zh": {
                "name": "中台设置",
                "fields": {
                    "retention_days": "数据保留天数",
                    "max_upload_mb": "最大上传(MB)",
                    "default_timezone": "默认时区",
                    "enable_quality_gate": "启用质量门禁",
                    "announcement": "公告",
                },
            }
        },
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    retention_days: int = Field(default=90)
    max_upload_mb: int = Field(default=100)
    default_timezone: str = Field(default="Asia/Shanghai")
    enable_quality_gate: bool = Field(default=True)
    announcement: Optional[str] = Field(
        default=None,
        sa_column_kwargs={"info": {"site_props": {"component": "textarea"}}},
    )
