"""
Health-check route — lightweight endpoint for load balancers, Docker health
checks, and uptime monitors.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "seoro"}
