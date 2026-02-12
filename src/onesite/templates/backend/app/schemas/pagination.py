from typing import TypeVar, Generic, List
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    total_pages: int

    @classmethod
    def create(cls, data: List[T], total: int, page: int, size: int) -> "PaginatedResponse[T]":
        return cls(
            items=data, total=total, page=page, size=size,
            total_pages=(total + size - 1) // size if size > 0 else 0
        )
