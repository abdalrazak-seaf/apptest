from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    environment: str


class DependencyCheck(BaseModel):
    ok: bool
    latency_ms: float
    # Exception class name only; never raw messages (they can leak hosts/credentials).
    error: str | None = None


class ReadinessResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    checks: dict[str, DependencyCheck]
