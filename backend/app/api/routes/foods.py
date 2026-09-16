"""
Foods API route — browse and search the food database.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from backend.app.nutrition.database import FoodDatabase

router = APIRouter(prefix="/foods", tags=["Foods"])

# These will be set during app initialization
_database: Optional[FoodDatabase] = None


def set_database(database: FoodDatabase) -> None:
    """Called during app startup to inject the database."""
    global _database
    _database = database


@router.get("")
async def list_foods(
    search: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
):
    """
    List or search food items in the database.

    Examples:
    - GET /foods -> all foods
    - GET /foods?search=paneer -> search for paneer
    - GET /foods?category=Curries -> filter by category
    """
    db = _database
    if db is None:
        raise HTTPException(status_code=503, detail="Food database not loaded.")

    if search:
        results = db.search(search, category=category, limit=limit)
    elif category:
        results = db.get_by_category(category)[:limit]
    else:
        results = db.get_all()[:limit]

    return {
        "foods": [r.to_dict() for r in results],
        "total": len(results),
        "categories": db.get_categories(),
    }


@router.get("/{food_id}")
async def get_food(food_id: str):
    """
    Get a specific food item by its ID.

    Example: GET /foods/IF002
    """
    db = _database
    if db is None:
        raise HTTPException(status_code=503, detail="Food database not loaded.")

    record = db.get_by_id(food_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Food '{food_id}' not found in the database.",
        )

    return record.to_dict()
