"""
FastAPI Application Entry Point — Phase 7

WHAT IT DOES:
    Creates the FastAPI application, initializes all components,
    and registers all API routes.

WHY WE NEED IT:
    This is the "main" file for the backend — everything starts here.

HOW TO RUN:
    cd indian-food-calorie-estimator
    python -m uvicorn backend.app.main:app --reload --port 8000

THEN VISIT:
    http://localhost:8000/docs    — Interactive API documentation
    http://localhost:8000/health  — Health check
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.utils.logger import logger


# ---------------------------------------------------------------------------
# Application lifespan — initialize components on startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all components when the server starts."""
    logger.info("=" * 60)
    logger.info("Starting Indian Food Calorie Estimation API")
    logger.info(f"  Environment: {settings.APP_ENV}")
    logger.info(f"  Vision mode: {settings.VISION_MODE}")
    logger.info(f"  Debug: {settings.DEBUG}")
    logger.info("=" * 60)

    # --- Initialize Vision Model ---
    if settings.is_gemini_mode:
        from backend.app.vision.gemini_detector import GeminiVisionModel
        vision_model = GeminiVisionModel(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
        )
        logger.info(f"Vision: Using Google Gemini ({settings.GEMINI_MODEL})")
    elif settings.is_claude_mode:
        from backend.app.vision.claude_detector import ClaudeVisionModel
        vision_model = ClaudeVisionModel(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.CLAUDE_MODEL,
        )
        logger.info(f"Vision: Using Claude ({settings.CLAUDE_MODEL})")
    else:
        from backend.app.vision.mock_detector import MockVisionModel
        vision_model = MockVisionModel()
        logger.info("Vision: Using Smart Local/Mock mode (no API key needed)")

    # --- Initialize RAG Pipeline ---
    logger.info("Initializing RAG pipeline...")
    from backend.app.rag.pipeline import RAGPipeline
    rag_pipeline = RAGPipeline(
        data_dir=str(settings.DATA_DIR),
        embedding_model_name=settings.EMBEDDING_MODEL,
        retrieval_threshold=settings.RETRIEVAL_THRESHOLD,
    )
    rag_pipeline.load_or_build()

    # --- Initialize Analysis Service ---
    from backend.app.services.analysis_service import AnalysisService
    analysis_service = AnalysisService(
        vision_model=vision_model,
        rag_pipeline=rag_pipeline,
    )

    # --- Inject dependencies into routes ---
    from backend.app.api.routes.foods import set_database
    from backend.app.api.routes.analyze import set_analysis_service

    set_database(rag_pipeline.database)
    set_analysis_service(analysis_service)

    # Create uploads directory
    settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("API ready! Visit http://localhost:8000/docs")
    logger.info("=" * 60)

    yield  # Application runs here

    # Cleanup on shutdown
    logger.info("Shutting down...")


# ---------------------------------------------------------------------------
# Create FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Indian Food Calorie Estimation API",
    description=(
        "AI-assisted Indian meal nutrition estimation. "
        "Upload a meal image to detect food items and estimate calories and nutrients.\n\n"
        "**Important:** All nutrition estimates are approximate and for informational "
        "purposes only. This is not medical or dietary advice."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register Routes ---
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.foods import router as foods_router
from backend.app.api.routes.analyze import router as analyze_router

app.include_router(health_router, tags=["Health"])
app.include_router(foods_router)
app.include_router(analyze_router)


# --- Root redirect to docs ---
@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API documentation."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")
