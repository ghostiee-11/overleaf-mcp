"""Uniform ToolResult shape returned by every tool."""
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ToolResult(BaseModel, Generic[T]):
    ok: bool
    data: T | None = None
    error: str | None = None
    suggestion: str | None = None


def ok(data: T) -> ToolResult[T]:
    return ToolResult(ok=True, data=data)


def fail(error: str, suggestion: str | None = None) -> ToolResult[Any]:
    return ToolResult(ok=False, error=error, suggestion=suggestion)
