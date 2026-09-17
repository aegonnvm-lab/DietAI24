"""
Tests for Phase 2 — Food Database

Tests cover:
  - CSV loading
  - Alias loading
  - Exact lookups (by ID, by name)
  - Alias lookups
  - Fuzzy matching (typos)
  - Category filtering
  - Search functionality
  - Unmatched food returns None
  - Integration with calculator
"""

import unittest
from pathlib import Path

from backend.app.nutrition.database import (
    FoodDatabase,
    FoodRecord,
    normalize_text,
)
from backend.app.nutrition.calculator import NutritionPer100g


# Find the project data directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = str(PROJECT_ROOT / "data" / "indian_foods.csv")
ALIASES_PATH = str(PROJECT_ROOT / "data" / "food_aliases.json")


class TestNormalizeText(unittest.TestCase):
    """Test the text normalization function."""

    def test_lowercase(self):
        self.assertEqual(normalize_text("Chicken Biryani"), "chicken biryani")

    def test_strip_whitespace(self):
        self.assertEqual(normalize_text("  roti  "), "roti")

    def test_collapse_spaces(self):
        self.assertEqual(normalize_text("dal  tadka"), "dal tadka")

    def test_remove_punctuation(self):
        self.assertEqual(normalize_text("biryani!"), "biryani")

    def test_preserve_hyphens(self):
        self.assertEqual(normalize_text("sugar-free"), "sugar-free")


class TestFoodDatabaseLoading(unittest.TestCase):
    """Test that the database loads correctly."""

    def setUp(self):
        self.db = FoodDatabase()
        self.db.load_csv(CSV_PATH)
        self.db.load_aliases(ALIASES_PATH)

    def test_loads_foods(self):
        """Should load food records from CSV (at least 50 foods)."""
        self.assertGreaterEqual(len(self.db.foods), 50)

    def test_loads_aliases(self):
        """Alias file should load many aliases."""
        self.assertGreater(len(self.db.aliases), 100)

    def test_csv_not_found(self):
        """Missing CSV should raise FileNotFoundError."""
        db = FoodDatabase()
        with self.assertRaises(FileNotFoundError):
            db.load_csv("nonexistent/path.csv")

    def test_all_foods_have_ids(self):
        """Every food must have a non-empty food_id."""
        for food_id, record in self.db.foods.items():
            self.assertTrue(bool(food_id))
            self.assertEqual(food_id, record.food_id)

    def test_all_foods_have_calories(self):
        """Every food must have positive calorie value."""
        for record in self.db.foods.values():
            self.assertGreater(record.calories_100g, 0, f"{record.food_name} has 0 calories")

    def test_get_categories(self):
        """Should return multiple categories."""
        categories = self.db.get_categories()
        self.assertGreater(len(categories), 5)
        self.assertIn("Curries", categories)
        self.assertIn("Rice Dishes", categories)


class TestFoodDatabaseLookup(unittest.TestCase):
    """Test various ways to look up food records."""

    def setUp(self):
        self.db = FoodDatabase()
        self.db.load_csv(CSV_PATH)
        self.db.load_aliases(ALIASES_PATH)

    def test_find_by_exact_id(self):
        """Look up by food_id should work."""
        record = self.db.get_by_id("IF002")
        self.assertIsNotNone(record)
        self.assertEqual(record.food_name, "Chicken Biryani")

    def test_find_by_name(self):
        """Look up by exact food name."""
        record = self.db.find("Chicken Biryani")
        self.assertIsNotNone(record)
        self.assertEqual(record.food_id, "IF002")

    def test_find_by_alias(self):
        """Look up by alias should find the correct food."""
        record = self.db.find("chapati")
        self.assertIsNotNone(record)
        self.assertEqual(record.food_id, "IF005")  # Roti

    def test_find_by_hindi_alias(self):
        """Hindi name alias should work."""
        record = self.db.find("dahi")
        self.assertIsNotNone(record)
        self.assertEqual(record.food_id, "IF039")  # Plain Curd

    def test_find_case_insensitive(self):
        """Search should be case-insensitive."""
        result1 = self.db.find("CHICKEN BIRYANI")
        result2 = self.db.find("chicken biryani")
        self.assertEqual(result1.food_id, result2.food_id)

    def test_find_fuzzy_match(self):
        """Slight misspelling should still match."""
        record = self.db.find("biriyni")  # missing 'a'
        self.assertIsNotNone(record)
        # Should match something biryani-related

    def test_find_unknown_returns_none(self):
        """Completely unrecognized food should return None."""
        record = self.db.find("xylophone")
        self.assertIsNone(record)

    def test_find_empty_returns_none(self):
        """Empty query should return None."""
        self.assertIsNone(self.db.find(""))
        self.assertIsNone(self.db.find("   "))

    def test_category_filter(self):
        """Category filter should return only matching foods."""
        breads = self.db.get_by_category("Breads")
        self.assertGreater(len(breads), 3)
        for bread in breads:
            self.assertEqual(bread.category, "Breads")

    def test_search_returns_results(self):
        """Search should return relevant results."""
        results = self.db.search("paneer")
        self.assertGreater(len(results), 0)
        # Paneer Butter Masala or Palak Paneer should be in results
        names = [r.food_name for r in results]
        self.assertTrue(
            any("paneer" in n.lower() for n in names),
            f"Expected paneer in results, got: {names}"
        )


class TestFoodRecordIntegration(unittest.TestCase):
    """Test that FoodRecord integrates with the calculator."""

    def setUp(self):
        self.db = FoodDatabase()
        self.db.load_csv(CSV_PATH)

    def test_to_nutrition_per_100g(self):
        """FoodRecord should convert to NutritionPer100g correctly."""
        record = self.db.get_by_id("IF002")  # Chicken Biryani
        nutrition = record.to_nutrition_per_100g()

        self.assertIsInstance(nutrition, NutritionPer100g)
        self.assertEqual(nutrition.calories_kcal, record.calories_100g)
        self.assertEqual(nutrition.protein_g, record.protein_100g)

    def test_embedding_text(self):
        """Embedding text should contain key information."""
        record = self.db.get_by_id("IF002")
        text = record.embedding_text()

        self.assertIn("Chicken Biryani", text)
        self.assertIn("Rice Dishes", text)
        self.assertIn("biryani", text.lower())

    def test_to_dict(self):
        """FoodRecord should serialize to dictionary."""
        record = self.db.get_by_id("IF001")
        d = record.to_dict()

        self.assertIn("food_id", d)
        self.assertIn("food_name", d)
        self.assertIn("calories_100g", d)
        self.assertEqual(d["source"], record.source)


if __name__ == "__main__":
    unittest.main()
