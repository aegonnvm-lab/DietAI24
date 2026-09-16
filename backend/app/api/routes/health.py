"""Health check route."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Simple health check endpoint.
    Returns the application status and configuration.
    """
    from backend.app.config import settings

    return {
        "status": "healthy",
        "app": "Indian Food Calorie Estimation API",
        "version": "1.0.0",
        "vision_mode": settings.VISION_MODE,
        "environment": settings.APP_ENV,
    }
