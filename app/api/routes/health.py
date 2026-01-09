"""Health check endpoints."""

from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/ready")
async def ready():
    """Readiness check endpoint.

    Returns 200 if the service is ready to accept requests.
    """
    return {"status": "ready"}
