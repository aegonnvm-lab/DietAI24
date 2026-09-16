"""
Vision Model Base — Phase 5

WHAT IT DOES:
    Defines the abstract interface that ALL vision models must follow.
    Whether we use mock mode, Google Gemini, Claude, or a local model,
    they all implement this same interface.

WHY WE NEED IT:
    We want to swap vision models without changing any other code.
    The analysis service just calls detect_foods(image) — it doesn't
    care which model is behind it.

HOW IT WORKS:
    VisionModel (abstract)
        ├── MockVisionModel      (returns sample data, no API needed)
        ├── ClaudeVisionModel    (uses Anthropic API with Claude)
        └── [future models]
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class DetectedFood:
    """
    A single food instance detected by the vision model.

    The vision model identifies WHAT food is present, WHERE it is, HOW MANY
    instances exist, and HOW confident it is.
    It does NOT provide nutrition values — that is strictly the database's job.
    """
    name: str                                        # Detected food name (e.g., "omelette")
    confidence: float                                # 0.0 to 1.0
    id: Optional[str] = None                         # Unique instance ID (e.g., "food_instance_1")
    count: int = 1                                   # Number of items (e.g., 2 for "2 rotis", 3 for "3 idlis")
    count_uncertain: bool = False                    # If true, visual count is ambiguous
    bounding_box: Optional[Dict[str, float]] = None  # Normalized [ymin, xmin, ymax, xmax]
    mask_available: bool = False                     # True if segmentation mask is computed
    mask_polygon: Optional[List[List[float]]] = None # Optional polygon contour points [[x, y], ...]
    estimated_grams: Optional[float] = None          # Visual mass estimate in grams
    visual_portion_size: Optional[str] = None        # "small", "medium", "large"
    visual_cues: Optional[str] = None                # Description of visual scale
    container_type: Optional[str] = None             # e.g., "katori", "plate", "bowl"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "confidence": round(self.confidence, 3),
            "count": self.count,
            "count_uncertain": self.count_uncertain,
            "bounding_box": self.bounding_box,
            "mask_available": self.mask_available,
            "mask_polygon": self.mask_polygon,
            "estimated_grams": self.estimated_grams,
            "visual_portion_size": self.visual_portion_size,
            "visual_cues": self.visual_cues,
            "container_type": self.container_type,
        }


@dataclass
class VisionResult:
    """
    Complete result from analyzing a meal image.

    Contains candidate food instances with bounding boxes, segmentation info,
    and metadata about the analysis.
    """
    foods: List[DetectedFood]
    model_name: str                      # Which model produced this result
    mode: str                            # "mock", "gemini", "claude", "yolo_sam", etc.
    candidate_regions_count: int = 0     # Number of candidate spatial proposals
    raw_response: Optional[str] = None  # Raw model output (for debugging)
    error: Optional[str] = None          # Error message if analysis failed

    @property
    def success(self) -> bool:
        return self.error is None and len(self.foods) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "foods": [f.to_dict() for f in self.foods],
            "model_name": self.model_name,
            "mode": self.mode,
            "food_count": len(self.foods),
            "candidate_regions_count": self.candidate_regions_count or len(self.foods),
            "error": self.error,
        }


class VisionModel(ABC):
    """
    Abstract base class for all vision models.

    Every vision model implementation must provide:
    - detect_foods(image_path) → VisionResult
    """

    @abstractmethod
    def detect_foods(self, image_path: str) -> VisionResult:
        """
        Analyze a meal image and detect food items.

        Args:
            image_path: Path to the image file on disk.

        Returns:
            VisionResult containing detected foods and metadata.
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable name of this model."""
        pass

    @property
    @abstractmethod
    def mode(self) -> str:
        """Mode identifier: 'mock', 'claude', 'gemini', etc."""
        pass
