"""
Analyze API route — the primary endpoint for meal image analysis.
"""

from typing import Optional
from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from backend.app.config import settings
from backend.app.schemas.analysis import AnalysisResponse, RecalculateRequest
from backend.app.services.analysis_service import AnalysisService
from backend.app.utils.file_utils import cleanup_file, save_upload, validate_image_file

router = APIRouter(tags=["Analysis"])

# These will be set during app initialization
_analysis_service: Optional[AnalysisService] = None


def set_analysis_service(service: AnalysisService) -> None:
    """Called during app startup to inject the analysis service."""
    global _analysis_service
    _analysis_service = service


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_meal(
    image: UploadFile = File(..., description="Meal image to analyze"),
    debug: bool = Query(False, description="Include debug information"),
):
    """
    Analyze a meal image and estimate nutrition.

    This is the PRIMARY endpoint — the whole pipeline runs here:
    Image -> Vision -> Normalization -> RAG -> Portion -> Calculation -> Results
    """
    service = _analysis_service
    if service is None:
        raise HTTPException(status_code=503, detail="Analysis service not initialized.")

    # Validate the uploaded image
    file_bytes = await image.read()

    is_valid, error_msg = validate_image_file(
        filename=image.filename or "unknown",
        content_type=image.content_type,
        file_size=len(file_bytes),
        max_size_mb=settings.MAX_IMAGE_SIZE_MB,
    )

    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Save to temporary file
    image_path = save_upload(
        file_bytes=file_bytes,
        original_filename=image.filename or "upload.jpg",
        upload_dir=str(settings.UPLOADS_DIR),
    )

    try:
        # Run the analysis pipeline
        result = service.analyze_image(
            image_path=image_path,
            debug=debug or settings.DEBUG_ANALYSIS,
        )
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}",
        )
    finally:
        # Clean up the temporary image file
        cleanup_file(image_path)


@router.post("/recalculate", response_model=AnalysisResponse)
async def recalculate_nutrition(request: RecalculateRequest):
    """
    Recalculate nutrition with user-corrected food items and portions.
    """
    service = _analysis_service
    if service is None:
        raise HTTPException(status_code=503, detail="Analysis service not initialized.")

    corrections = [
        {"food_id": item.food_id, "portion_grams": item.portion_grams}
        for item in request.foods
    ]

    result = service.recalculate(corrections)
    return result
