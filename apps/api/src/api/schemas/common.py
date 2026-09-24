"""Shapes shared by several endpoints."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Every error body. `code` is stable; clients translate it."""

    code: str
    details: dict[str, object] | None = None


class Ack(BaseModel):
    ok: bool = True
