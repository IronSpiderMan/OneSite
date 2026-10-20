"""Hierarchy model used by the tree-leaf visualization example."""

from typing import Optional

from sqlmodel import Field, SQLModel

from onesite.config import OneSiteConfig, TreeLeafConfig, TreeViewConfig


class AssetFolder(SQLModel, table=True):
    __tablename__ = "asset_folder"

    __onesite__ = OneSiteConfig(
        icon="Folders",
        tree_view=TreeViewConfig(
            leaf=TreeLeafConfig(
                model="AssetDocument",
                parent_field="folder_id",
                label_field="name",
                page_size=20,
            )
        ),
        translations={
            "zh": {
                "name": "资产目录",
                "fields": {
                    "name": "目录名称",
                    "parent_id": "上级目录",
                    "description": "目录说明",
                },
            }
        },
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(
        index=True,
        sa_column_kwargs={"info": {"site_props": {"is_search_field": True}}},
    )
    # Root nodes use NULL.  The generated tree API accepts parent_id=0 as the
    # query sentinel for those NULL roots.
    parent_id: Optional[int] = Field(default=None, foreign_key="asset_folder.id")
    description: Optional[str] = None
