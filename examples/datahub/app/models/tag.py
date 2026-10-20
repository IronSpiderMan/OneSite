from sqlmodel import Field, SQLModel


class Tag(SQLModel, table=True):
    __tablename__ = "tag"

    __onesite__ = {
        "icon": "Tag",
        "translations": {
            "zh": {"name": "标签", "fields": {"name": "标签名", "color": "颜色", "description": "描述"}}
        },
    }

    id: int = Field(primary_key=True)
    name: str = Field(unique=True, index=True)
    color: str = Field(default="#2563EB")
    description: str = Field(default="")
