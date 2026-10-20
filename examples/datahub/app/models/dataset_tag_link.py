from sqlmodel import Field, SQLModel


class DatasetTagLink(SQLModel, table=True):
    __tablename__ = "dataset_tag_link"

    __onesite__ = {"is_link_table": True}

    id: int = Field(primary_key=True)
    dataset_id: int = Field(foreign_key="dataset.id")
    tag_id: int = Field(foreign_key="tag.id")
