"""
Unit Tests for Food Normalization & Matching Logic
Phase 3 & Phase 9
"""

import pytest
from backend.app.nutrition.database import FoodDatabase


@pytest.fixture(scope="module")
def db():
    database = FoodDatabase()
    database.load_csv("data/indian_foods.csv")
    database.load_aliases("data/food_aliases.json")
    return database


class TestFoodNormalization:
    def test_case_insensitivity(self, db):
        # All upper, all lower, mixed
        match_lower = db.find("chicken biryani")
        match_upper = db.find("CHICKEN BIRYANI")
        match_mixed = db.find("ChIcKeN BiRyAnI")

        assert match_lower is not None
        assert match_upper is not None
        assert match_mixed is not None
        assert match_lower.food_id == match_upper.food_id == match_mixed.food_id

    def test_whitespace_and_punctuation_handling(self, db):
        # Extra spaces, leading/trailing whitespace
        match_spaces = db.find("   roti   ")
        assert match_spaces is not None
        assert match_spaces.food_name == "Roti"

    def test_alias_resolution(self, db):
        # Common vernacular and spelling aliases
        assert db.find("chapati") is not None
        assert db.find("chapati").food_name == "Roti"

        assert db.find("dal") is not None
        assert "Dal" in db.find("dal").food_name

        assert db.find("dahi") is not None
        assert db.find("dahi").food_name == "Plain Curd"

        assert db.find("paneer makhani") is not None
        assert db.find("paneer makhani").food_name == "Paneer Butter Masala"

    def test_fuzzy_matching(self, db):
        # Minor typos
        match_typo = db.find("chiken biryani")
        assert match_typo is not None
        assert match_typo.food_name == "Chicken Biryani"

        match_typo2 = db.find("palak paner")
        assert match_typo2 is not None
        assert match_typo2.food_name == "Palak Paneer"

    def test_unknown_queries(self, db):
        # Non-food gibberish should return None
        assert db.find("xyzqwert123456789") is None
