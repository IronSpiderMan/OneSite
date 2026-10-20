"""Leaf records displayed below asset folders in the tree example."""

from typing import Optional

from sqlmodel import Field, SQLModel


class AssetDocument(SQLModel, table=True):
    __tablename__ = "asset_document"

    __onesite__ = {
        "icon": "FileText",
        "translations": {
            "zh": {
                "name": "资产文档",
                "fields": {
                    "name": "文档名称",
                    "folder_id": "所属目录",
                    "content": "文档内容",
                },
            }
        },
    }

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(
        index=True,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    folder_id: int = Field(foreign_key="asset_folder.id")
    content: str
