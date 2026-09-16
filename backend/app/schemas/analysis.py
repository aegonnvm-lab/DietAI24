"""
Analysis Schemas — Phase 7

Pydantic models for the meal analysis API response.
This is the primary output of the entire pipeline.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PortionSchema(BaseModel):
    """Portion size estimation details."""
    size_label: str = Field(..., description="Size category: small, medium, large, custom")
    estimated_grams: float = Field(..., description="Estimated weight in grams")
    method: str = Field(..., description="Estimation method (e.g., MVP_RULE_BASED)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Estimation confidence")


class NutritionSchema(BaseModel):
    """Calculated nutrition for a specific portion."""
    calories_kcal: float = Field(..., description="Calories (kcal)")
    protein_g: float = Field(..., description="Protein (g)")
    carbs_g: float = Field(..., description="Carbohydrates (g)")
    fat_g: float = Field(..., description="Fat (g)")
    fiber_g: Optional[float] = Field(None, description="Fiber (g), null if unavailable")


class AnalyzedFoodItem(BaseModel):
    """A single food item in the analysis result."""
    instance_id: str = Field(default="food_instance_1", description="Instance identifier for region tracking")
    detected_name: str = Field(..., description="Name as detected by vision model")
    standardized_name: str = Field(..., description="Standardized name from database")
    food_id: str = Field(..., description="Food database ID")
    category: str = Field(..., description="Food category")
    count: int = Field(default=1, description="Instance count (e.g. 2 for 2 rotis)")
    count_uncertain: bool = Field(default=False, description="True if visual count is ambiguous")
    recognition_confidence: float = Field(..., ge=0.0, le=1.0, description="Vision model confidence")
    retrieval_confidence: str = Field(..., description="Database match confidence: high, medium, low, fallback")
    retrieval_score: float = Field(..., ge=0.0, le=1.0, description="RAG similarity score")
    match_status: str = Field(default="HIGH_CONFIDENCE", description="Exact match status code")
    needs_user_review: bool = Field(default=False, description="True if user verification is advised")
    detection: Optional[Dict[str, Any]] = Field(default=None, description="Spatial detection metadata (bbox, mask)")
    nutrition_match: Optional[Dict[str, Any]] = Field(default=None, description="Detailed database retrieval metadata")
    portion: PortionSchema
    nutrition: NutritionSchema
    source: str = Field(..., description="Nutrition data source")


class MealTotals(BaseModel):
    """Aggregated nutrition for the entire meal."""
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: Optional[float] = None
    total_weight_g: float
    macro_split: Dict[str, float] = Field(
        ...,
        description="Percentage of calories from each macro (protein_pct, carbs_pct, fat_pct)"
    )


class AnalysisDebugInfo(BaseModel):
    """Debug information about the analysis pipeline (only in debug mode)."""
    vision_mode: str
    vision_model: str
    vision_raw_response: Optional[str] = None
    retrieval_details: Optional[List[Dict[str, Any]]] = None
    portion_method: str = "MVP_RULE_BASED"
    candidate_regions_count: int = 0


class AnalysisResponse(BaseModel):
    """
    Complete meal analysis response — the primary API output.

    This is what the frontend receives after analyzing a meal image.
    """
    status: str = Field(..., description="'success' or 'error'")
    analysis_id: str = Field(..., description="Unique analysis identifier")
    image: Optional[Dict[str, Any]] = Field(default=None, description="Image dimensions and metadata")
    foods: List[AnalyzedFoodItem] = Field(default_factory=list, description="Detected and analyzed foods")
    totals: Optional[MealTotals] = Field(None, description="Meal nutrition totals")
    food_count: int = Field(0, description="Number of foods detected")
    vision_mode: str = Field(..., description="'mock', 'gemini', or 'claude'")
    warnings: List[str] = Field(default_factory=list, description="Quality and uncertainty warnings")
    disclaimer: str = Field(
        default=(
            "These nutrition estimates are approximate and for informational purposes only. "
            "Values are based on standardized database records and estimated portion sizes. "
            "This is not medical or dietary advice."
        ),
        description="Important disclaimer about estimate accuracy",
    )
    debug: Optional[AnalysisDebugInfo] = Field(None, description="Debug info (only when DEBUG_ANALYSIS=true)")
    error: Optional[str] = Field(None, description="Error message if status is 'error'")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "analysis_id": "abc123",
                "food_count": 2,
                "vision_mode": "mock",
                "foods": [
                    {
                        "detected_name": "chicken biryani",
                        "standardized_name": "Chicken Biryani",
                        "food_id": "IF002",
                        "category": "Rice Dishes",
                        "recognition_confidence": 0.92,
                        "retrieval_confidence": "high",
                        "retrieval_score": 0.95,
                        "portion": {
                            "size_label": "medium",
                            "estimated_grams": 250,
                            "method": "MVP_RULE_BASED",
                            "confidence": 0.5,
                        },
                        "nutrition": {
                            "calories_kcal": 450.0,
                            "protein_g": 23.8,
                            "carbs_g": 55.0,
                            "fat_g": 15.5,
                            "fiber_g": 3.0,
                        },
                        "source": "DEMO_APPROXIMATE",
                    }
                ],
                "totals": {
                    "calories_kcal": 450.0,
                    "protein_g": 23.8,
                    "carbs_g": 55.0,
                    "fat_g": 15.5,
                    "fiber_g": 3.0,
                    "total_weight_g": 250.0,
                    "macro_split": {"protein_pct": 21.1, "carbs_pct": 48.9, "fat_pct": 30.0},
                },
                "disclaimer": "These nutrition estimates are approximate...",
            }
        }
    )


class FoodCorrectionItem(BaseModel):
    """A single food correction from the user."""
    food_id: str = Field(..., description="Food ID (or new food ID if changed)")
    portion_grams: float = Field(..., gt=0, description="Corrected portion in grams")


class RecalculateRequest(BaseModel):
    """Request to recalculate nutrition with user corrections."""
    foods: List[FoodCorrectionItem] = Field(..., description="Corrected food items")
