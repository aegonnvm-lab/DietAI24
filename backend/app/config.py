"""
Application Configuration — Phase 7

WHAT IT DOES:
    Loads all configuration from environment variables.
    Provides a single Settings object used across the application.

WHY WE NEED IT:
    We don't want API keys, model names, or file paths hard-coded.
    Environment variables make it easy to switch between mock/real mode,
    change thresholds, or deploy to different environments.

HOW TO USE:
    Copy .env.example to .env and edit the values.
    The Settings class automatically reads from the .env file.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        # Load .env file if it exists
        self._load_dotenv()

        # --- Application ---
        self.APP_ENV: str = os.getenv("APP_ENV", "development")
        self.DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
        self.DEBUG_ANALYSIS: bool = os.getenv("DEBUG_ANALYSIS", "false").lower() == "true"

        # --- Vision ---
        self.VISION_MODE: str = os.getenv("VISION_MODE", "mock").lower()
        self.ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
        self.CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
        self.GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

        # --- Embeddings / RAG ---
        self.EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.TOP_K: int = int(os.getenv("TOP_K", "5"))
        self.RETRIEVAL_THRESHOLD: float = float(os.getenv("RETRIEVAL_THRESHOLD", "0.3"))

        # --- Data paths ---
        self.PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
        self.DATA_DIR: Path = self.PROJECT_ROOT / "data"
        self.CSV_PATH: Path = self.DATA_DIR / "indian_foods.csv"
        self.ALIASES_PATH: Path = self.DATA_DIR / "food_aliases.json"
        self.FAISS_INDEX_PATH: Path = self.DATA_DIR / "faiss_index.bin"
        self.UPLOADS_DIR: Path = self.PROJECT_ROOT / "uploads"

        # --- File handling ---
        self.MAX_IMAGE_SIZE_MB: float = float(os.getenv("MAX_IMAGE_SIZE_MB", "10"))
        self.ALLOWED_IMAGE_TYPES: set = {"image/jpeg", "image/png", "image/webp", "image/gif"}

        # --- Server ---
        self.HOST: str = os.getenv("HOST", "0.0.0.0")
        self.PORT: int = int(os.getenv("PORT", "8000"))
        self.CORS_ORIGINS: list = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
        ).split(",")

    def _load_dotenv(self):
        """Load .env file if python-dotenv is available."""
        try:
            from dotenv import load_dotenv
            # Look for .env in the backend directory
            env_path = Path(__file__).resolve().parent.parent / ".env"
            if env_path.exists():
                load_dotenv(env_path)
            # Also try project root
            root_env = Path(__file__).resolve().parent.parent.parent / ".env"
            if root_env.exists():
                load_dotenv(root_env)
        except ImportError:
            pass  # python-dotenv not installed, rely on system env vars

    @property
    def is_mock_mode(self) -> bool:
        return self.VISION_MODE == "mock"

    @property
    def is_gemini_mode(self) -> bool:
        return self.VISION_MODE == "gemini"

    @property
    def is_claude_mode(self) -> bool:
        return self.VISION_MODE == "claude"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def max_image_bytes(self) -> int:
        return int(self.MAX_IMAGE_SIZE_MB * 1024 * 1024)


# Singleton instance
settings = Settings()
