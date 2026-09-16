"""
Structured Logging — Phase 7

WHAT IT DOES:
    Sets up application logging with structured, readable format.
    Logs pipeline stages (vision, retrieval, calculation) with request context.

WHY WE NEED IT:
    When debugging "why did it estimate 600 kcal for my dal?", we need
    to trace every step: what the vision model saw, what the retriever
    matched, what portion was estimated, and what was calculated.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional


def setup_logger(
    name: str = "indian_food_estimator",
    level: str = "INFO",
) -> logging.Logger:
    """
    Set up a structured logger for the application.

    Args:
        name: Logger name.
        level: Logging level ("DEBUG", "INFO", "WARNING", "ERROR").

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Console handler with structured format
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


# Application-wide logger instance
logger = setup_logger()
