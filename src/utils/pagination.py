from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, Field

T = TypeVar('T')


class PaginationParams(BaseModel):
    """Pagination parameters for requests"""
    
    page: int = Field(default=1, ge=1, description="Page number (starts from 1)")
    page_size: int = Field(default=20, ge=1, le=100, description="Number of items per page")


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper"""
    
    items: list[T] = Field(..., description="List of items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
    
    @classmethod
    def create(
        cls,
        items: list[T],
        page: int,
        page_size: int,
        total_items: int
    ) -> "PaginatedResponse[T]":
        """Create paginated response with calculated metadata"""
        total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
        return cls(
            items=items,
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total_items=total_items,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_previous=page > 1
            )
        )
