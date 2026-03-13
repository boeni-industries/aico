from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T] = Field(default_factory=list)
    total: int = Field(...)
    page: int = Field(...)
    page_size: int = Field(...)
    total_pages: int = Field(...)
