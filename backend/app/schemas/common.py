"""Shared response envelope and pagination helpers."""
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Unified success envelope: {success, message, data}."""

    success: bool = True
    message: str = ""
    data: T | None = None


class ApiErrorBody(BaseModel):
    """Unified error body returned by every failing endpoint."""

    success: bool = False
    message: str
    error_code: str


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int
    pages: int
