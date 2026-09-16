"""
Tests for Phase 1 — Nutrition Calculator

These tests verify that the core calculation math is correct.
They cover:
  - Normal calculations
  - Zero portion
  - Large portion
  - Negative values (should raise error)
  - Missing fiber (None)
  - Meal totals
  - Macro percentage split
  - Edge cases
"""

import unittest

from backend.app.nutrition.calculator import (
    CalculationError,
    MealNutrition,
    NutritionPer100g,
    PortionNutrition,
    calculate_meal,
    calculate_nutrition,
)


class TestCalculateNutrition(unittest.TestCase):
    """Test the core calculate_nutrition function."""

    def setUp(self):
        """Create a sample nutrition profile used across multiple tests."""
        self.biryani = NutritionPer100g(
            calories_kcal=180.0,
            protein_g=9.5,
            carbs_g=22.0,
            fat_g=6.2,
            fiber_g=1.2,
        )

    def test_basic_calculation(self):
        """180 kcal/100g × 250g = 450 kcal — the example from the project spec."""
        result = calculate_nutrition("Chicken Biryani", self.biryani, 250.0)

        self.assertEqual(result.food_name, "Chicken Biryani")
        self.assertEqual(result.portion_grams, 250.0)
        self.assertEqual(result.calories_kcal, 450.0)
        self.assertEqual(result.protein_g, 23.8)  # 9.5 × 2.5
        self.assertEqual(result.carbs_g, 55.0)    # 22.0 × 2.5
        self.assertEqual(result.fat_g, 15.5)      # 6.2 × 2.5
        self.assertEqual(result.fiber_g, 3.0)     # 1.2 × 2.5

    def test_100g_portion_returns_same_values(self):
        """100g portion should return the exact same values as per-100g."""
        result = calculate_nutrition("Test", self.biryani, 100.0)

        self.assertEqual(result.calories_kcal, 180.0)
        self.assertEqual(result.protein_g, 9.5)
        self.assertEqual(result.carbs_g, 22.0)
        self.assertEqual(result.fat_g, 6.2)
        self.assertEqual(result.fiber_g, 1.2)

    def test_zero_portion(self):
        """0g portion should return all zeros — not an error."""
        result = calculate_nutrition("Nothing", self.biryani, 0.0)

        self.assertEqual(result.calories_kcal, 0.0)
        self.assertEqual(result.protein_g, 0.0)
        self.assertEqual(result.carbs_g, 0.0)
        self.assertEqual(result.fat_g, 0.0)
        self.assertEqual(result.fiber_g, 0.0)

    def test_small_portion(self):
        """A small 10g portion should correctly scale down."""
        result = calculate_nutrition("Taste", self.biryani, 10.0)

        self.assertEqual(result.calories_kcal, 18.0)  # 180 × 0.1
        self.assertEqual(result.protein_g, 1.0)        # 9.5 × 0.1 = 0.95 → rounds to 1.0

    def test_negative_portion_raises_error(self):
        """Negative portion weight should be rejected."""
        with self.assertRaises(CalculationError) as ctx:
            calculate_nutrition("Bad", self.biryani, -50.0)
        self.assertIn("negative", str(ctx.exception).lower())

    def test_extremely_large_portion_raises_error(self):
        """Unrealistically large portion (>10kg) should be rejected."""
        with self.assertRaises(CalculationError) as ctx:
            calculate_nutrition("Huge", self.biryani, 15_000.0)
        self.assertIn("unrealistically large", str(ctx.exception).lower())

    def test_negative_calories_raises_error(self):
        """Negative calorie values in nutrition data should be rejected."""
        bad_nutrition = NutritionPer100g(
            calories_kcal=-100.0, protein_g=5.0, carbs_g=10.0, fat_g=3.0
        )
        with self.assertRaises(CalculationError):
            calculate_nutrition("Bad", bad_nutrition, 100.0)

    def test_missing_fiber_returns_none(self):
        """When fiber is not available (None), result should also be None."""
        no_fiber = NutritionPer100g(
            calories_kcal=100.0, protein_g=5.0, carbs_g=20.0, fat_g=2.0, fiber_g=None
        )
        result = calculate_nutrition("No Fiber Data", no_fiber, 200.0)

        self.assertIsNone(result.fiber_g)
        self.assertEqual(result.calories_kcal, 200.0)  # Other values still calculated

    def test_rounding(self):
        """Results should be rounded to 1 decimal place by default."""
        odd_nutrition = NutritionPer100g(
            calories_kcal=133.33, protein_g=7.77, carbs_g=18.88, fat_g=4.44, fiber_g=2.22
        )
        result = calculate_nutrition("Odd", odd_nutrition, 150.0)

        # 133.33 × 1.5 = 199.995 → 200.0
        self.assertEqual(result.calories_kcal, 200.0)
        # 7.77 × 1.5 = 11.655 → 11.7
        self.assertEqual(result.protein_g, 11.7)

    def test_custom_rounding(self):
        """Custom rounding precision should work."""
        result = calculate_nutrition("Test", self.biryani, 250.0, round_to=0)
        self.assertEqual(result.calories_kcal, 450)  # integer-like

    def test_to_dict(self):
        """Result should be convertible to a dictionary for JSON serialization."""
        result = calculate_nutrition("Biryani", self.biryani, 100.0)
        d = result.to_dict()

        self.assertIsInstance(d, dict)
        self.assertEqual(d["food_name"], "Biryani")
        self.assertEqual(d["calories_kcal"], 180.0)
        self.assertIn("portion_grams", d)
        self.assertIn("protein_g", d)
        self.assertIn("carbs_g", d)
        self.assertIn("fat_g", d)
        self.assertIn("fiber_g", d)


class TestCalculateMeal(unittest.TestCase):
    """Test meal aggregation — combining multiple food items."""

    def setUp(self):
        """Create sample food results for meal tests."""
        biryani_per_100g = NutritionPer100g(
            calories_kcal=180.0, protein_g=9.5, carbs_g=22.0,
            fat_g=6.2, fiber_g=1.2,
        )
        roti_per_100g = NutritionPer100g(
            calories_kcal=297.0, protein_g=9.2, carbs_g=55.8,
            fat_g=3.7, fiber_g=10.7,
        )

        self.biryani = calculate_nutrition("Chicken Biryani", biryani_per_100g, 250.0)
        self.roti = calculate_nutrition("Roti (2 pieces)", roti_per_100g, 70.0)

    def test_meal_totals(self):
        """Meal totals should be the sum of individual items."""
        meal = calculate_meal([self.biryani, self.roti])

        self.assertEqual(len(meal.items), 2)
        # 450.0 + 207.9 = 657.9
        self.assertAlmostEqual(
            meal.total_calories_kcal,
            self.biryani.calories_kcal + self.roti.calories_kcal,
            places=1,
        )
        self.assertAlmostEqual(
            meal.total_protein_g,
            self.biryani.protein_g + self.roti.protein_g,
            places=1,
        )
        self.assertEqual(meal.total_weight_g, 250.0 + 70.0)

    def test_meal_macro_split(self):
        """Macro percentages should sum to approximately 100%."""
        meal = calculate_meal([self.biryani, self.roti])

        total_pct = (
            meal.macro_split["protein_pct"]
            + meal.macro_split["carbs_pct"]
            + meal.macro_split["fat_pct"]
        )
        # Should be close to 100% (rounding may cause tiny deviation)
        self.assertAlmostEqual(total_pct, 100.0, places=0)

    def test_empty_meal(self):
        """Empty meal should return all zeros."""
        meal = calculate_meal([])

        self.assertEqual(meal.total_calories_kcal, 0.0)
        self.assertEqual(meal.total_protein_g, 0.0)
        self.assertEqual(len(meal.items), 0)

    def test_single_item_meal(self):
        """Single-item meal total should equal that item."""
        meal = calculate_meal([self.biryani])

        self.assertEqual(meal.total_calories_kcal, self.biryani.calories_kcal)
        self.assertEqual(len(meal.items), 1)

    def test_meal_to_dict(self):
        """Meal result should be fully serializable to dict."""
        meal = calculate_meal([self.biryani, self.roti])
        d = meal.to_dict()

        self.assertIsInstance(d, dict)
        self.assertIn("items", d)
        self.assertIn("total_calories_kcal", d)
        self.assertIn("macro_split", d)
        self.assertEqual(len(d["items"]), 2)


class TestNutritionPer100g(unittest.TestCase):
    """Test the input data model."""

    def test_to_dict(self):
        """NutritionPer100g should convert to dictionary."""
        nutrition = NutritionPer100g(
            calories_kcal=100.0, protein_g=5.0, carbs_g=20.0, fat_g=2.0
        )
        d = nutrition.to_dict()

        self.assertEqual(d["calories_kcal"], 100.0)
        self.assertIsNone(d["fiber_g"])  # default is None

    def test_fiber_default_none(self):
        """Fiber should default to None when not provided."""
        nutrition = NutritionPer100g(
            calories_kcal=100.0, protein_g=5.0, carbs_g=20.0, fat_g=2.0
        )
        self.assertIsNone(nutrition.fiber_g)


if __name__ == "__main__":
    unittest.main()
