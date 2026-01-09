"""API routes."""

from fastapi import APIRouter

from .conversations import router as conversations_router
from .analysis import router as analysis_router
from .health import router as health_router


router = APIRouter()

router.include_router(conversations_router, prefix="/conversations", tags=["conversations"])
router.include_router(analysis_router, prefix="/analyze", tags=["analysis"])
router.include_router(health_router, tags=["health"])
