"""
API Integration Tests — Phase 7 & 9

Tests the FastAPI application endpoints:
- GET /health
- GET /foods
- GET /foods/{food_id}
- POST /analyze (with mock detector)
- POST /recalculate
"""

import io
from fastapi.testclient import TestClient
import pytest
from PIL import Image

from backend.app.main import app
from backend.app.nutrition.database import FoodDatabase
from backend.app.services.analysis_service import AnalysisService
from backend.app.vision.mock_detector import MockVisionModel
from backend.app.api.routes.foods import set_database
from backend.app.api.routes.analyze import set_analysis_service


@pytest.fixture(scope="module")
def client():
    # Load default database
    db = FoodDatabase()
    db.load_csv("data/indian_foods.csv")
    db.load_aliases("data/food_aliases.json")
    set_database(db)

    # Setup analysis service with mock vision and mock RAG pipeline
    class MockRAG:
        def __init__(self, database):
            self.database = database
        def retrieve(self, query, top_k=5):
            rec = self.database.find(query)
            if not rec:
                rec = self.database.get_all()[0]
            from backend.app.rag.retriever import RetrievalResult
            return [RetrievalResult(food_record=rec, similarity_score=0.9, rank=1, raw_distance=0.1)]

    service = AnalysisService(
        vision_model=MockVisionModel(),
        rag_pipeline=MockRAG(db),
    )
    set_analysis_service(service)

    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_list_foods(client):
    response = client.get("/foods")
    assert response.status_code == 200
    data = response.json()
    assert "foods" in data
    assert len(data["foods"]) > 0
    assert "categories" in data


def test_search_foods(client):
    response = client.get("/foods?search=biryani")
    assert response.status_code == 200
    data = response.json()
    assert len(data["foods"]) > 0
    names = [f["food_name"].lower() for f in data["foods"]]
    assert any("biryani" in name for name in names)


def test_get_food_by_id(client):
    response = client.get("/foods/IF001")
    assert response.status_code == 200
    data = response.json()
    assert data["food_id"] == "IF001"
    assert "calories_100g" in data


def test_get_food_by_invalid_id(client):
    response = client.get("/foods/NONEXISTENT_FOOD_999")
    assert response.status_code == 404


def test_analyze_image(client):
    # Create a small valid test image in memory
    img_byte_arr = io.BytesIO()
    img = Image.new("RGB", (100, 100), color="red")
    img.save(img_byte_arr, format="JPEG")
    img_byte_arr.seek(0)

    response = client.post(
        "/analyze",
        files={"image": ("test_meal.jpg", img_byte_arr, "image/jpeg")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "foods" in data
    assert "totals" in data
    assert data["totals"]["calories_kcal"] > 0
    assert len(data["foods"]) > 0


def test_recalculate(client):
    payload = {
        "foods": [
            {"food_id": "IF001", "portion_grams": 200.0}
        ]
    }
    response = client.post("/recalculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "foods" in data
    assert data["foods"][0]["portion"]["estimated_grams"] == 200.0
    assert data["totals"]["calories_kcal"] > 0
