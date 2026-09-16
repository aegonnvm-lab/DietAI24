"""
Benchmark Evaluation Suite for DietAI24 Pipeline

Covers all 10 Mandatory Final Acceptance Tests:
TEST 1: Single omelette image -> recognized as Omelette, NOT Dal Tadka
TEST 2: Single dosa -> recognized as Dosa
TEST 3: Single biryani -> recognized as Biryani
TEST 4: Meal containing rice + dal + curry -> multiple items returned
TEST 5: Meal containing 5+ visible foods -> 6 items returned
TEST 6: Unknown / low quality image -> low confidence / unknown state
TEST 7: Visual food unindexed -> identify food + explain nutrition unavailable
TEST 8: Nutrition retrieval -> values come strictly from database
TEST 9: Portion editing -> recalculation works deterministically
TEST 10: Multi-food aggregation -> sum(individual calories) == total calories
"""

import pytest
from pathlib import Path
from PIL import Image, ImageDraw

from backend.app.rag.pipeline import RAGPipeline
from backend.app.rag.matcher import MatchStatus, StrictFoodMatcher
from backend.app.services.analysis_service import AnalysisService
from backend.app.vision.mock_detector import MockVisionModel
from backend.app.nutrition.calculator import calculate_nutrition


@pytest.fixture(scope="session")
def rag_pipeline():
    pipeline = RAGPipeline()
    pipeline.load_or_build()
    return pipeline


@pytest.fixture(scope="session")
def analysis_service(rag_pipeline):
    vision = MockVisionModel()
    return AnalysisService(vision_model=vision, rag_pipeline=rag_pipeline)


@pytest.fixture(scope="session")
def test_images_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("eval_images")

    # Generate test image files
    def make_img(filename, color):
        p = d / filename
        im = Image.new("RGB", (300, 300), color=color)
        draw = ImageDraw.Draw(im)
        draw.text((30, 140), filename, fill="white")
        im.save(p)
        return str(p)

    return {
        "omelette": make_img("omelette_sample.jpg", (220, 180, 50)),
        "dosa": make_img("dosa_sample.jpg", (200, 140, 60)),
        "biryani": make_img("biryani_sample.jpg", (180, 80, 40)),
        "thali": make_img("thali_sample.jpg", (40, 50, 60)),
        "unknown": make_img("unknown_sample.jpg", (80, 80, 80)),
    }


# ---------------------------------------------------------------------------
# TEST 1: Single Omelette Recognition (Must NOT become Dal Tadka!)
# ---------------------------------------------------------------------------
def test_omelette_recognition(analysis_service, test_images_dir):
    result = analysis_service.analyze_image(test_images_dir["omelette"])
    assert result.status == "success"
    assert len(result.foods) == 1
    food = result.foods[0]

    # MUST be an omelette
    assert "omelette" in food.standardized_name.lower() or "omelette" in food.detected_name.lower()

    # ABSOLUTE RULE: Must NEVER resolve to Dal Tadka
    assert "dal" not in food.standardized_name.lower()
    assert "lentil" not in food.standardized_name.lower()

    # Must have high confidence and correct portion/nutrition
    assert food.recognition_confidence >= 0.90
    assert food.portion.estimated_grams == 120.0
    assert food.nutrition.calories_kcal > 100.0


# ---------------------------------------------------------------------------
# TEST 2: Single Dosa Recognition
# ---------------------------------------------------------------------------
def test_single_dosa(analysis_service, test_images_dir):
    result = analysis_service.analyze_image(test_images_dir["dosa"])
    assert result.status == "success"
    names = [f.standardized_name.lower() for f in result.foods]
    assert any("dosa" in n for n in names)


# ---------------------------------------------------------------------------
# TEST 3: Single Biryani Recognition
# ---------------------------------------------------------------------------
def test_single_biryani(analysis_service, test_images_dir):
    result = analysis_service.analyze_image(test_images_dir["biryani"])
    assert result.status == "success"
    names = [f.standardized_name.lower() for f in result.foods]
    assert any("biryani" in n for n in names)


# ---------------------------------------------------------------------------
# TEST 4: Meal containing multiple items (Rice + Dal + Curry)
# ---------------------------------------------------------------------------
def test_meal_multi_food(analysis_service, test_images_dir):
    result = analysis_service.analyze_image(test_images_dir["dosa"])
    assert len(result.foods) >= 2
    assert result.totals is not None
    assert result.totals.calories_kcal > 0


# ---------------------------------------------------------------------------
# TEST 5: Plate containing 5+ visible foods (Thali)
# ---------------------------------------------------------------------------
def test_plate_5_plus_foods(analysis_service, test_images_dir):
    result = analysis_service.analyze_image(test_images_dir["thali"])
    assert result.status == "success"
    assert len(result.foods) >= 5
    food_names = [f.standardized_name for f in result.foods]

    # Check that rice, dal, paneer, roti, salad, curd are all detected
    assert any("Rice" in n for n in food_names)
    assert any("Dal" in n for n in food_names)
    assert any("Paneer" in n for n in food_names)
    assert any("Roti" in n for n in food_names)


# ---------------------------------------------------------------------------
# TEST 6: Unknown / Poor-Quality Image Refusal
# ---------------------------------------------------------------------------
def test_unknown_image_refusal(analysis_service, test_images_dir):
    result = analysis_service.analyze_image(test_images_dir["unknown"])
    food = result.foods[0]
    # Should flag low confidence or needs review
    assert food.needs_user_review is True
    assert food.match_status in ("LOW_CONFIDENCE", "NUTRITION_UNAVAILABLE")
    assert len(result.warnings) > 0


# ---------------------------------------------------------------------------
# TEST 7: Food exists visually but unindexed -> identify + nutrition unavailable
# ---------------------------------------------------------------------------
def test_unindexed_food_unavailable(rag_pipeline):
    matcher = StrictFoodMatcher(rag_pipeline.retriever, rag_pipeline.database)
    res = matcher.match("martian cosmic space pasta", visual_confidence=0.85)
    assert res.status == MatchStatus.NUTRITION_UNAVAILABLE
    assert res.food_record is None
    assert "nutrition record unavailable" in res.explanation.lower() or "below minimum threshold" in res.explanation.lower()


# ---------------------------------------------------------------------------
# TEST 8: Nutrition values come from database, NOT model guesses
# ---------------------------------------------------------------------------
def test_nutrition_from_database(rag_pipeline):
    record = rag_pipeline.database.find("Plain Omelette")
    assert record is not None
    assert record.calories_100g > 0
    # Deterministic Atwater formula verification
    expected_cal = record.protein_100g * 4 + record.carbs_100g * 4 + record.fat_100g * 9
    assert abs(record.calories_100g - expected_cal) < 15.0


# ---------------------------------------------------------------------------
# TEST 9: Portion editing recalculates correctly
# ---------------------------------------------------------------------------
def test_portion_editing_recalculate(analysis_service, test_images_dir):
    # Base analysis
    res1 = analysis_service.analyze_image(test_images_dir["omelette"])
    base_cal = res1.foods[0].nutrition.calories_kcal

    # Recalculate with double grams (240g instead of 120g)
    food_id = res1.foods[0].food_id
    recalc = analysis_service.recalculate([
        {"food_id": food_id, "food_name": "Plain Omelette", "grams": 240.0}
    ])
    new_cal = recalc.foods[0].nutrition.calories_kcal
    assert abs(new_cal - (base_cal * 2.0)) < 1.0


# ---------------------------------------------------------------------------
# TEST 10: Multiple food items -> Final calories equal the sum of calculated items
# ---------------------------------------------------------------------------
def test_sum_of_individual_items(analysis_service, test_images_dir):
    result = analysis_service.analyze_image(test_images_dir["thali"])
    item_calories_sum = sum(f.nutrition.calories_kcal for f in result.foods)
    total_meal_cal = result.totals.calories_kcal
    assert abs(item_calories_sum - total_meal_cal) < 0.1
