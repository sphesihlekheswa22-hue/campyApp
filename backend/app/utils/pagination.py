from typing import Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import Query

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


def paginate(query: Query, limit: int = 50, offset: int = 0):
    limit = min(max(limit, 1), 500)
    offset = max(offset, 0)
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return items, total, limit, offset
