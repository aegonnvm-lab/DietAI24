import unittest
from backend.nutrition_calculator import NutritionCalculator, FoodItem, NutritionalInfo


class TestNutritionCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = NutritionCalculator()

    def test_database_loaded(self):
        foods = self.calc.get_all_foods()
        self.assertGreater(len(foods), 30)

    def test_find_food(self):
        roti = self.calc.find_food("roti")
        self.assertIsNotNone(roti)
        self.assertEqual(roti.id, "roti_chapati")

    def test_calculate_item_nutrition_conversions(self):
        # 1 piece of roti is ~35g
        nutrition = self.calc.calculate_item_nutrition("roti", quantity=2, unit="piece")
        self.assertEqual(nutrition.serving_weight_g, 70.0)
        self.assertAlmostEqual(nutrition.calories, 297.0 * 0.7, places=1)

    def test_calculate_meal(self):
        meal = [
            {"food": "roti", "quantity": 2, "unit": "piece"},
            {"food": "dal_tadka", "quantity": 1, "unit": "katori"},
        ]
        summary = self.calc.calculate_meal(meal)
        self.assertGreater(summary.total_calories, 200)
        self.assertIn("protein", summary.macro_percentages)
        self.assertIn("carbohydrates", summary.macro_percentages)
        self.assertIn("fat", summary.macro_percentages)

    def test_bmr_and_tdee(self):
        bmr = self.calc.calculate_bmr(weight_kg=70, height_cm=175, age=25, gender="male")
        self.assertGreater(bmr, 1400)
        tdee = self.calc.calculate_tdee(bmr, activity_level="moderately_active")
        self.assertGreater(tdee, bmr)


if __name__ == "__main__":
    unittest.main()
