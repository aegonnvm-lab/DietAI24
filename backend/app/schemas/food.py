"""
Food Schemas — Phase 7

Pydantic models for food-related API responses.
These define the EXACT shape of JSON data returned by the API.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class FoodNutritionSchema(BaseModel):
    """Nutrition values for a food item."""
    calories_100g: float = Field(..., description="Calories per 100g (kcal)")
    protein_100g: float = Field(..., description="Protein per 100g (g)")
    carbs_100g: float = Field(..., description="Carbohydrates per 100g (g)")
    fat_100g: float = Field(..., description="Fat per 100g (g)")
    fiber_100g: float = Field(..., description="Dietary fiber per 100g (g)")


class FoodSchema(BaseModel):
    """Complete food record as returned by the API."""
    food_id: str = Field(..., description="Unique food identifier (e.g., IF002)")
    food_name: str = Field(..., description="Standardized food name")
    aliases: List[str] = Field(default_factory=list, description="Alternative names")
    category: str = Field(..., description="Food category")
    nutrition: FoodNutritionSchema
    default_portion_g: float = Field(..., description="Default portion size (grams)")
    source: str = Field(..., description="Data source indicator")
    notes: str = Field(default="", description="Food description")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "food_id": "IF002",
                "food_name": "Chicken Biryani",
                "aliases": ["biryani", "biriyani"],
                "category": "Rice Dishes",
                "nutrition": {
                    "calories_100g": 180.0,
                    "protein_100g": 9.5,
                    "carbs_100g": 22.0,
                    "fat_100g": 6.2,
                    "fiber_100g": 1.2,
                },
                "default_portion_g": 250.0,
                "source": "DEMO_APPROXIMATE",
                "notes": "Fragrant basmati rice with spiced chicken",
            }
        }
    )


class FoodListSchema(BaseModel):
    """List of food records."""
    foods: List[FoodSchema]
    total: int
    categories: List[str]
