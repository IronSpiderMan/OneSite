"""Built-in geographic location value object for JSON-backed model fields."""

from typing import Optional

from sqlmodel import Field, SQLModel


class Location(SQLModel):
    """A validated latitude/longitude pair stored as a JSON object."""

    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
