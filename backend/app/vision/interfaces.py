"""
Modular Vision Interfaces — Phase 5 Upgrade

Defines decoupled interfaces for:
1. FoodDetector: Proposes spatial candidate regions / bounding boxes.
2. FoodSegmenter: Generates fine-grained segmentation masks for detected regions.
3. FoodClassifier: Classifies food within each detected region/crop.

This allows plugging in SAM2, YOLO, GroundingDINO, Google Gemini, or local models
without altering the core application.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class BoundingBox:
    """
    Normalized bounding box coordinates [ymin, xmin, ymax, xmax]
    Values are between 0.0 and 1.0 relative to image width and height.
    """
    ymin: float
    xmin: float
    ymax: float
    xmax: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "ymin": round(self.ymin, 4),
            "xmin": round(self.xmin, 4),
            "ymax": round(self.ymax, 4),
            "xmax": round(self.xmax, 4),
        }

    @property
    def width(self) -> float:
        return max(0.0, self.xmax - self.xmin)

    @property
    def height(self) -> float:
        return max(0.0, self.ymax - self.ymin)

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass
class FoodCandidateRegion:
    """A spatial region in the meal image candidate for food presence."""
    region_id: str
    bbox: BoundingBox
    mask_polygon: Optional[List[Tuple[float, float]]] = None  # Normalized (x, y) coordinates
    confidence: float = 0.80
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClassificationResult:
    """Individual food classification for a specific crop/region."""
    canonical_name: str
    raw_label: str
    confidence: float
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    visible_cues: Optional[str] = None
    count: int = 1
    count_uncertain: bool = False
    is_food: bool = True


class FoodDetector(ABC):
    """Proposes candidate food regions and bounding boxes across the meal image."""

    @abstractmethod
    def detect_regions(self, image_path: str) -> List[FoodCandidateRegion]:
        """Detect candidate regions containing food items."""
        pass


class FoodSegmenter(ABC):
    """Generates segmentation masks for candidate regions."""

    @abstractmethod
    def segment_region(self, image_path: str, bbox: BoundingBox) -> Optional[List[Tuple[float, float]]]:
        """Compute fine-grained boundary mask polygon for the region."""
        pass


class FoodClassifier(ABC):
    """Classifies an individual cropped food region."""

    @abstractmethod
    def classify_crop(self, image_path: str, bbox: BoundingBox) -> ClassificationResult:
        """Classify what food item is present in this region."""
        pass
