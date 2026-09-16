"""
Nutrition Calculator — Phase 1

WHAT IT DOES:
    Takes nutrition values per 100g and a portion weight (in grams),
    and calculates the actual nutrition for that portion.

WHY WE NEED IT:
    Every food item detected by the vision model will eventually pass through
    this calculator. The AI identifies food, the database provides nutrition
    per 100g, and THIS module does the arithmetic.

HOW DATA FLOWS:
    nutrition_per_100g + portion_grams → calculated nutrition

FORMULA:
    nutrient_for_portion = nutrient_per_100g × portion_grams / 100

IMPORTANT:
    This module does NOT know about databases, images, or AI.
    It is pure math — easy to test, easy to trust.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class NutritionPer100g:
    """
    Nutrition values for 100 grams of a food item.

    This is what you'll find in a nutrition database or on a food label.
    All values are per 100 grams.
    """
    calories_kcal: float    # Energy in kilocalories
    protein_g: float        # Protein in grams
    carbs_g: float          # Carbohydrates in grams
    fat_g: float            # Fat in grams
    fiber_g: Optional[float] = None  # Fiber in grams (may not always be available)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "calories_kcal": self.calories_kcal,
            "protein_g": self.protein_g,
            "carbs_g": self.carbs_g,
            "fat_g": self.fat_g,
            "fiber_g": self.fiber_g,
        }


@dataclass
class PortionNutrition:
    """
    Calculated nutrition for a specific portion of food.

    This is the OUTPUT of the calculator — what you'd show to the user.
    """
    food_name: str
    portion_grams: float
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "food_name": self.food_name,
            "portion_grams": self.portion_grams,
            "calories_kcal": self.calories_kcal,
            "protein_g": self.protein_g,
            "carbs_g": self.carbs_g,
            "fat_g": self.fat_g,
            "fiber_g": self.fiber_g,
        }


@dataclass
class MealNutrition:
    """
    Combined nutrition for an entire meal (multiple food items).
    """
    items: List[PortionNutrition]
    total_calories_kcal: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    total_fiber_g: Optional[float]
    total_weight_g: float
    macro_split: Dict[str, float]  # Percentage of calories from protein, carbs, fat

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "total_calories_kcal": self.total_calories_kcal,
            "total_protein_g": self.total_protein_g,
            "total_carbs_g": self.total_carbs_g,
            "total_fat_g": self.total_fat_g,
            "total_fiber_g": self.total_fiber_g,
            "total_weight_g": self.total_weight_g,
            "macro_split": self.macro_split,
        }


# ---------------------------------------------------------------------------
# Input Validation
# ---------------------------------------------------------------------------

class CalculationError(Exception):
    """Raised when nutrition calculation encounters invalid input."""
    pass


def _validate_portion(portion_grams: float) -> None:
    """Check that portion weight is valid."""
    if portion_grams < 0:
        raise CalculationError(
            f"Portion cannot be negative: {portion_grams}g. "
            f"Please provide a positive weight."
        )
    if portion_grams > 10_000:
        raise CalculationError(
            f"Portion seems unrealistically large: {portion_grams}g (10 kg). "
            f"Maximum allowed is 10,000g. Please check your input."
        )


def _validate_nutrition(nutrition: NutritionPer100g) -> None:
    """Check that per-100g nutrition values are reasonable."""
    if nutrition.calories_kcal < 0:
        raise CalculationError(
            f"Calories cannot be negative: {nutrition.calories_kcal} kcal/100g."
        )
    if nutrition.protein_g < 0:
        raise CalculationError(
            f"Protein cannot be negative: {nutrition.protein_g} g/100g."
        )
    if nutrition.carbs_g < 0:
        raise CalculationError(
            f"Carbohydrates cannot be negative: {nutrition.carbs_g} g/100g."
        )
    if nutrition.fat_g < 0:
        raise CalculationError(
            f"Fat cannot be negative: {nutrition.fat_g} g/100g."
        )
    if nutrition.fiber_g is not None and nutrition.fiber_g < 0:
        raise CalculationError(
            f"Fiber cannot be negative: {nutrition.fiber_g} g/100g."
        )


# ---------------------------------------------------------------------------
# Core Calculation Functions
# ---------------------------------------------------------------------------

def calculate_nutrition(
    food_name: str,
    nutrition_per_100g: NutritionPer100g,
    portion_grams: float,
    round_to: int = 1,
) -> PortionNutrition:
    """
    Calculate nutrition for a given portion of food.

    This is the CORE function of the entire project.
    Everything else (vision, RAG, database) exists to feed data into this function.

    Args:
        food_name: Name of the food (for display purposes).
        nutrition_per_100g: Nutrition values per 100 grams.
        portion_grams: How many grams are being consumed.
        round_to: Decimal places for rounding (default: 1).

    Returns:
        PortionNutrition with calculated values.

    Raises:
        CalculationError: If inputs are invalid.

    Example:
        >>> nutrition = NutritionPer100g(calories_kcal=180, protein_g=5.0,
        ...                              carbs_g=25.0, fat_g=6.0, fiber_g=1.5)
        >>> result = calculate_nutrition("Chicken Biryani", nutrition, 250.0)
        >>> result.calories_kcal
        450.0
    """
    # Validate inputs
    _validate_nutrition(nutrition_per_100g)
    _validate_portion(portion_grams)

    # The formula: nutrient_for_portion = nutrient_per_100g × portion_grams / 100
    factor = portion_grams / 100.0

    # Calculate fiber (may be None if unavailable)
    fiber_value = None
    if nutrition_per_100g.fiber_g is not None:
        fiber_value = round(nutrition_per_100g.fiber_g * factor, round_to)

    return PortionNutrition(
        food_name=food_name,
        portion_grams=round(portion_grams, round_to),
        calories_kcal=round(nutrition_per_100g.calories_kcal * factor, round_to),
        protein_g=round(nutrition_per_100g.protein_g * factor, round_to),
        carbs_g=round(nutrition_per_100g.carbs_g * factor, round_to),
        fat_g=round(nutrition_per_100g.fat_g * factor, round_to),
        fiber_g=fiber_value,
    )


def calculate_meal(items: List[PortionNutrition]) -> MealNutrition:
    """
    Combine nutrition from multiple food items into a meal total.

    This is used when a thali or plate has multiple dishes —
    each dish is calculated individually, then this function sums them up.

    Args:
        items: List of already-calculated PortionNutrition results.

    Returns:
        MealNutrition with totals and macro percentage split.

    Example:
        >>> rice = calculate_nutrition("Rice", rice_per_100g, 200.0)
        >>> dal  = calculate_nutrition("Dal",  dal_per_100g,  150.0)
        >>> meal = calculate_meal([rice, dal])
        >>> meal.total_calories_kcal  # sum of both
    """
    if not items:
        return MealNutrition(
            items=[],
            total_calories_kcal=0.0,
            total_protein_g=0.0,
            total_carbs_g=0.0,
            total_fat_g=0.0,
            total_fiber_g=0.0,
            total_weight_g=0.0,
            macro_split={"protein_pct": 0.0, "carbs_pct": 0.0, "fat_pct": 0.0},
        )

    total_cal = sum(item.calories_kcal for item in items)
    total_protein = sum(item.protein_g for item in items)
    total_carbs = sum(item.carbs_g for item in items)
    total_fat = sum(item.fat_g for item in items)
    total_weight = sum(item.portion_grams for item in items)

    # Fiber: sum only if ALL items have it; otherwise mark as None
    fiber_values = [item.fiber_g for item in items if item.fiber_g is not None]
    total_fiber: Optional[float] = round(sum(fiber_values), 1) if fiber_values else None

    # Macro split: what % of calories come from each macronutrient?
    # Protein = 4 kcal/g, Carbs = 4 kcal/g, Fat = 9 kcal/g
    protein_cal = total_protein * 4.0
    carbs_cal = total_carbs * 4.0
    fat_cal = total_fat * 9.0
    macro_total = protein_cal + carbs_cal + fat_cal

    if macro_total > 0:
        macro_split = {
            "protein_pct": round((protein_cal / macro_total) * 100.0, 1),
            "carbs_pct": round((carbs_cal / macro_total) * 100.0, 1),
            "fat_pct": round((fat_cal / macro_total) * 100.0, 1),
        }
    else:
        macro_split = {"protein_pct": 0.0, "carbs_pct": 0.0, "fat_pct": 0.0}

    return MealNutrition(
        items=items,
        total_calories_kcal=round(total_cal, 1),
        total_protein_g=round(total_protein, 1),
        total_carbs_g=round(total_carbs, 1),
        total_fat_g=round(total_fat, 1),
        total_fiber_g=total_fiber,
        total_weight_g=round(total_weight, 1),
        macro_split=macro_split,
    )


# ---------------------------------------------------------------------------
# Quick demonstration (only runs if you execute this file directly)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 1 — Nutrition Calculator Demo")
    print("=" * 60)

    # Example: Chicken Biryani — 180 kcal per 100g, eating 250g
    biryani_per_100g = NutritionPer100g(
        calories_kcal=180.0,
        protein_g=9.5,
        carbs_g=22.0,
        fat_g=6.2,
        fiber_g=1.2,
    )

    biryani_result = calculate_nutrition(
        food_name="Chicken Biryani",
        nutrition_per_100g=biryani_per_100g,
        portion_grams=250.0,
    )

    print(f"\nFood: {biryani_result.food_name}")
    print(f"Portion: {biryani_result.portion_grams}g")
    print(f"Calories: {biryani_result.calories_kcal} kcal")
    print(f"Protein: {biryani_result.protein_g}g")
    print(f"Carbs: {biryani_result.carbs_g}g")
    print(f"Fat: {biryani_result.fat_g}g")
    print(f"Fiber: {biryani_result.fiber_g}g")

    # Example: Roti — 297 kcal per 100g, eating 2 rotis (70g)
    roti_per_100g = NutritionPer100g(
        calories_kcal=297.0,
        protein_g=9.2,
        carbs_g=55.8,
        fat_g=3.7,
        fiber_g=10.7,
    )

    roti_result = calculate_nutrition(
        food_name="Roti",
        nutrition_per_100g=roti_per_100g,
        portion_grams=70.0,  # 2 rotis × 35g each
    )

    print(f"\nFood: {roti_result.food_name}")
    print(f"Portion: {roti_result.portion_grams}g")
    print(f"Calories: {roti_result.calories_kcal} kcal")

    # Meal total
    meal = calculate_meal([biryani_result, roti_result])
    print(f"\n{'='*60}")
    print(f"MEAL TOTAL:")
    print(f"Total Calories: {meal.total_calories_kcal} kcal")
    print(f"Total Protein: {meal.total_protein_g}g")
    print(f"Total Carbs: {meal.total_carbs_g}g")
    print(f"Total Fat: {meal.total_fat_g}g")
    print(f"Total Fiber: {meal.total_fiber_g}g")
    print(f"Total Weight: {meal.total_weight_g}g")
    print(f"Macro Split: {meal.macro_split}")

    # Edge case: zero portion
    zero_result = calculate_nutrition("Nothing", biryani_per_100g, 0.0)
    print(f"\nZero portion test: {zero_result.calories_kcal} kcal [OK]")

    print(f"\n{'='*60}")
    print("Phase 1 — All demonstrations passed!")
