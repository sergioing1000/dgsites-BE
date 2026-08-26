"""Health check endpoint.

Provides a lightweight ``GET /health`` route that returns a stable
JSON payload indicating service availability.  Designed for load
balancers, uptime monitors, and promotion-readiness gates.
"""

from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter(tags=["health"])

APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")


@router.get(
    "/health",
    summary="Service health check",
    description=(
        "Returns service status, version, and environment. "
        "Use for readiness probes and promotion gates."
    ),
    response_description="Health status payload.",
)
async def health_check() -> dict[str, str]:
    """Return a stable health-check response.

    The response shape is intentionally fixed so that consumers can
    rely on it without versioning concerns:

    .. code-block:: json

        {
            "status": "healthy",
            "version": "1.0.0",
            "environment": "local"
        }

    Returns:
        Dict with ``status``, ``version``, and ``environment`` keys.
    """
    return {
        "status": "healthy",
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
    }
