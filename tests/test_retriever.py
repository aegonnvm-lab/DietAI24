"""
Unit Tests for RAG Retriever & Pipeline
Tests the retrieval results, distance conversions, ranking, and pipeline logic.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock

from backend.app.nutrition.database import FoodRecord, FoodDatabase
from backend.app.rag.retriever import FoodRetriever, RetrievalResult
from backend.app.rag.index import FAISSIndex


def create_sample_food(food_id: str, name: str, calories: float = 200.0) -> FoodRecord:
    return FoodRecord(
        food_id=food_id,
        food_name=name,
        aliases=[name.lower()],
        category="Main Dishes",
        calories_100g=calories,
        protein_100g=10.0,
        carbs_100g=25.0,
        fat_100g=5.0,
        fiber_100g=2.0,
        default_portion_g=150.0,
        source="DEMO_APPROXIMATE",
        notes="Test record",
    )


class TestRetrievalResult:
    def test_confidence_labels(self):
        food = create_sample_food("test_1", "Paneer Tikka")
        
        # High confidence (>= 0.7)
        res_high = RetrievalResult(food_record=food, similarity_score=0.85, rank=1, raw_distance=0.17)
        assert res_high.is_high_confidence is True
        assert res_high.is_low_confidence is False
        assert res_high.confidence_label == "high"

        # Medium confidence (0.4 <= score < 0.7)
        res_med = RetrievalResult(food_record=food, similarity_score=0.55, rank=1, raw_distance=0.81)
        assert res_med.is_high_confidence is False
        assert res_med.is_low_confidence is False
        assert res_med.confidence_label == "medium"

        # Low confidence (< 0.4)
        res_low = RetrievalResult(food_record=food, similarity_score=0.25, rank=2, raw_distance=3.0)
        assert res_low.is_high_confidence is False
        assert res_low.is_low_confidence is True
        assert res_low.confidence_label == "low"

    def test_to_dict(self):
        food = create_sample_food("test_1", "Butter Naan")
        res = RetrievalResult(food_record=food, similarity_score=0.92345, rank=1, raw_distance=0.08)
        d = res.to_dict()
        assert d["food_id"] == "test_1"
        assert d["food_name"] == "Butter Naan"
        assert d["similarity_score"] == 0.923
        assert d["confidence"] == "high"
        assert d["rank"] == 1


class TestFoodRetriever:
    def test_distance_to_similarity(self):
        # Distance 0 -> 1.0
        assert FoodRetriever._distance_to_similarity(0.0) == 1.0
        # Distance 1 -> 0.5
        assert FoodRetriever._distance_to_similarity(1.0) == 0.5
        # Distance 9 -> 0.1
        assert pytest.approx(FoodRetriever._distance_to_similarity(9.0)) == 0.1

    def test_retrieve_with_direct_match(self):
        db = MagicMock(spec=FoodDatabase)
        food_biryani = create_sample_food("biryani_1", "Chicken Biryani")
        db.find.return_value = food_biryani
        db.get_by_id.side_effect = lambda fid: food_biryani if fid == "biryani_1" else None

        emb_model = MagicMock()
        emb_model.embed.return_value = np.zeros(384, dtype=np.float32)

        faiss_idx = MagicMock()
        # Mock search returning distance 0.2 for index 0
        faiss_idx.search.return_value = (np.array([[0.2]]), np.array([[0]]))

        retriever = FoodRetriever(
            database=db,
            embedding_model=emb_model,
            faiss_index=faiss_idx,
            food_id_order=["biryani_1"],
            retrieval_threshold=0.3,
        )

        results = retriever.retrieve("Chicken Biryani", top_k=1)
        assert len(results) == 1
        assert results[0].food_record.food_name == "Chicken Biryani"
        assert results[0].similarity_score == 0.95  # boosted for direct match
        assert results[0].rank == 1

    def test_retrieve_best_below_threshold(self):
        db = MagicMock(spec=FoodDatabase)
        db.find.return_value = None
        db.get_by_id.return_value = create_sample_food("unknown_food", "Mystery Stew")

        emb_model = MagicMock()
        emb_model.embed.return_value = np.zeros(384, dtype=np.float32)

        faiss_idx = MagicMock()
        # High distance -> similarity ~ 0.09 (below threshold 0.3)
        faiss_idx.search.return_value = (np.array([[10.0]]), np.array([[0]]))

        retriever = FoodRetriever(
            database=db,
            embedding_model=emb_model,
            faiss_index=faiss_idx,
            food_id_order=["unknown_food"],
            retrieval_threshold=0.3,
        )

        best = retriever.retrieve_best("Random Unknown Query")
        assert best is None
