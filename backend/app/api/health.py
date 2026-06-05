"""Health check router."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return service health status."""
    return HealthResponse(status="ok")
