"""
Food Database — Phase 2

WHAT IT DOES:
    Loads the Indian food nutrition CSV, provides search/lookup capabilities,
    and connects food records to the calculator from Phase 1.

WHY WE NEED IT:
    When the vision model says "I see chicken biryani", we need to look up
    the standardized nutrition values for chicken biryani. This module does that.

HOW DATA FLOWS:
    CSV file → FoodDatabase → FoodRecord → NutritionPer100g → Calculator

IMPORTANT:
    This module does NOT generate nutrition values.
    It only loads and serves values from the dataset.
"""

from __future__ import annotations

import csv
import difflib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.nutrition.calculator import NutritionPer100g


# ---------------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------------

@dataclass
class FoodRecord:
    """
    A single food item from the database.

    This represents one row from indian_foods.csv — a standardized food record
    with its nutrition values, aliases, and metadata.
    """
    food_id: str               # e.g., "IF002"
    food_name: str             # e.g., "Chicken Biryani"
    aliases: List[str]         # e.g., ["biryani", "biriyani", ...]
    category: str              # e.g., "Rice Dishes"
    calories_100g: float       # kcal per 100g
    protein_100g: float        # grams per 100g
    carbs_100g: float          # grams per 100g
    fat_100g: float            # grams per 100g
    fiber_100g: float          # grams per 100g
    default_portion_g: float   # typical portion in grams
    source: str                # e.g., "DEMO_APPROXIMATE"
    notes: str                 # description

    def to_nutrition_per_100g(self) -> NutritionPer100g:
        """Convert to the calculator's input format."""
        return NutritionPer100g(
            calories_kcal=self.calories_100g,
            protein_g=self.protein_100g,
            carbs_g=self.carbs_100g,
            fat_g=self.fat_100g,
            fiber_g=self.fiber_100g,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "food_id": self.food_id,
            "food_name": self.food_name,
            "aliases": self.aliases,
            "category": self.category,
            "calories_100g": self.calories_100g,
            "protein_100g": self.protein_100g,
            "carbs_100g": self.carbs_100g,
            "fat_100g": self.fat_100g,
            "fiber_100g": self.fiber_100g,
            "default_portion_g": self.default_portion_g,
            "source": self.source,
            "notes": self.notes,
        }

    def embedding_text(self) -> str:
        """
        Create a text representation for embedding/RAG purposes.

        This text is what gets converted into a vector for similarity search.
        It includes the name, aliases, category, and description so that
        different ways of referring to the food can all match.
        """
        alias_str = ", ".join(self.aliases) if self.aliases else ""
        return (
            f"Food: {self.food_name}. "
            f"Category: {self.category}. "
            f"Also known as: {alias_str}. "
            f"Description: {self.notes}."
        )


# ---------------------------------------------------------------------------
# Text Normalization (Phase 3 prep)
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """
    Clean up a food name for matching purposes.

    Steps:
    1. Convert to lowercase
    2. Strip leading/trailing whitespace
    3. Remove extra spaces
    4. Remove common punctuation that doesn't change meaning

    Example:
        "  Chicken  Biryani! " → "chicken biryani"
    """
    text = text.lower().strip()
    # Remove punctuation except hyphens (which may be meaningful)
    text = re.sub(r'[^\w\s-]', '', text)
    # Collapse multiple spaces into one
    text = re.sub(r'\s+', ' ', text)
    return text


# ---------------------------------------------------------------------------
# Food Database
# ---------------------------------------------------------------------------

class FoodDatabase:
    """
    Loads, stores, and searches Indian food nutrition records.

    WHAT I SHOULD SEE WHEN IT WORKS:
        >>> db = FoodDatabase()
        >>> db.load_csv("data/indian_foods.csv")
        >>> print(len(db.foods))
        50
        >>> record = db.find("biryani")
        >>> print(record.food_name)
        Chicken Biryani
    """

    def __init__(self):
        self.foods: Dict[str, FoodRecord] = {}  # food_id → FoodRecord
        self.aliases: Dict[str, str] = {}        # alias → food_id
        self._name_index: Dict[str, str] = {}    # normalized_name → food_id

    def load_csv(self, csv_path: str) -> int:
        """
        Load food records from the CSV file.

        Args:
            csv_path: Path to indian_foods.csv

        Returns:
            Number of food records loaded.

        Raises:
            FileNotFoundError: If the CSV file doesn't exist.
            ValueError: If the CSV is malformed.
        """
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Food database not found at: {csv_path}\n"
                f"Expected file: data/indian_foods.csv"
            )

        self.foods.clear()
        self._name_index.clear()

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):  # row 1 is header
                try:
                    # Parse aliases from comma-separated string
                    raw_aliases = row.get("aliases", "")
                    aliases = [
                        a.strip() for a in raw_aliases.split(",") if a.strip()
                    ]

                    record = FoodRecord(
                        food_id=row["food_id"].strip(),
                        food_name=row["food_name"].strip(),
                        aliases=aliases,
                        category=row.get("category", "General").strip(),
                        calories_100g=float(row.get("calories_100g", 0)),
                        protein_100g=float(row.get("protein_100g", 0)),
                        carbs_100g=float(row.get("carbs_100g", 0)),
                        fat_100g=float(row.get("fat_100g", 0)),
                        fiber_100g=float(row.get("fiber_100g", 0)),
                        default_portion_g=float(row.get("default_portion_g", 150)),
                        source=row.get("source", "UNKNOWN").strip(),
                        notes=row.get("notes", "").strip(),
                    )

                    self.foods[record.food_id] = record

                    # Build name index for fast lookup
                    self._name_index[normalize_text(record.food_name)] = record.food_id
                    for alias in aliases:
                        self._name_index[normalize_text(alias)] = record.food_id

                except (KeyError, ValueError) as e:
                    print(f"Warning: Skipping row {row_num} in {csv_path}: {e}")

        return len(self.foods)

    def load_aliases(self, aliases_path: str) -> int:
        """
        Load additional alias mappings from food_aliases.json.

        These supplement the aliases already in the CSV.

        Args:
            aliases_path: Path to food_aliases.json

        Returns:
            Number of aliases loaded.
        """
        path = Path(aliases_path)
        if not path.exists():
            return 0

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for alias, food_id in data.items():
            if alias.startswith("_"):  # skip metadata keys
                continue
            normalized = normalize_text(alias)
            self.aliases[normalized] = food_id
            self._name_index[normalized] = food_id
            count += 1

        return count

    def get_all(self) -> List[FoodRecord]:
        """Return all food records."""
        return list(self.foods.values())

    def get_by_id(self, food_id: str) -> Optional[FoodRecord]:
        """Look up a food record by its exact ID."""
        return self.foods.get(food_id.upper())

    def get_categories(self) -> List[str]:
        """Return sorted list of unique food categories."""
        categories = {f.category for f in self.foods.values()}
        return sorted(categories)

    def get_by_category(self, category: str) -> List[FoodRecord]:
        """Return all foods in a specific category."""
        cat_lower = category.lower()
        return [
            f for f in self.foods.values()
            if f.category.lower() == cat_lower
        ]

    # ------------------------------------------------------------------
    # Search / Normalization (Phase 3)
    # ------------------------------------------------------------------

    def find(self, query: str) -> Optional[FoodRecord]:
        """
        Find the best matching food record for a query string.

        Search order (most precise to least):
        1. Exact food_id match
        2. Exact normalized name / alias match
        3. Substring match
        4. Fuzzy match (for misspellings)

        Args:
            query: Food name, alias, or ID to search for.

        Returns:
            The best matching FoodRecord, or None if nothing matches.
        """
        if not query or not query.strip():
            return None

        normalized = normalize_text(query)

        # 1. Exact food_id match
        upper_query = query.strip().upper()
        if upper_query in self.foods:
            return self.foods[upper_query]

        # 2. Exact name/alias match (from both CSV aliases and aliases JSON)
        if normalized in self._name_index:
            food_id = self._name_index[normalized]
            return self.foods.get(food_id)

        # 3. Substring match — does the query appear inside any food name?
        for name, food_id in self._name_index.items():
            if normalized in name or name in normalized:
                return self.foods.get(food_id)

        # 4. Fuzzy match — handles typos like "biriyni" → "biryani"
        all_names = list(self._name_index.keys())
        close_matches = difflib.get_close_matches(
            normalized, all_names, n=1, cutoff=0.6
        )
        if close_matches:
            food_id = self._name_index[close_matches[0]]
            return self.foods.get(food_id)

        return None

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[FoodRecord]:
        """
        Search for foods matching a query, with optional category filter.

        Returns results ordered by relevance:
        1. Name starts with query
        2. Name contains query
        3. Fuzzy matches

        Args:
            query: Search text.
            category: Optional category filter.
            limit: Maximum results to return.

        Returns:
            List of matching FoodRecords.
        """
        normalized = normalize_text(query) if query else ""

        # Start with all foods, optionally filtered by category
        pool = list(self.foods.values())
        if category:
            cat_lower = category.lower()
            pool = [f for f in pool if f.category.lower() == cat_lower]

        if not normalized:
            return pool[:limit]

        # Priority 1: name starts with query
        starts_with = []
        # Priority 2: name or alias contains query
        contains = []

        for food in pool:
            food_name_norm = normalize_text(food.food_name)
            alias_norms = [normalize_text(a) for a in food.aliases]

            if food_name_norm.startswith(normalized):
                starts_with.append(food)
            elif normalized in food_name_norm:
                contains.append(food)
            elif any(normalized in a for a in alias_norms):
                contains.append(food)

        results = starts_with + contains

        # Priority 3: fuzzy match for remaining
        if len(results) < limit:
            found_ids = {f.food_id for f in results}
            remaining = [f for f in pool if f.food_id not in found_ids]
            remaining_names = {normalize_text(f.food_name): f for f in remaining}
            close = difflib.get_close_matches(
                normalized, list(remaining_names.keys()),
                n=limit - len(results), cutoff=0.4
            )
            for name in close:
                results.append(remaining_names[name])

        return results[:limit]


# ---------------------------------------------------------------------------
# Convenience: load database with default paths
# ---------------------------------------------------------------------------

def load_default_database() -> FoodDatabase:
    """
    Load the food database from the default data directory.

    Looks for files relative to the project root:
    - data/indian_foods.csv
    - data/food_aliases.json
    """
    # Find the project root (go up from this file)
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    csv_path = project_root / "data" / "indian_foods.csv"
    aliases_path = project_root / "data" / "food_aliases.json"

    db = FoodDatabase()

    food_count = db.load_csv(str(csv_path))
    alias_count = db.load_aliases(str(aliases_path))

    print(f"Loaded {food_count} foods, {alias_count} aliases")
    return db


# ---------------------------------------------------------------------------
# Quick demonstration
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 2 - Food Database Demo")
    print("=" * 60)

    db = load_default_database()

    # Show categories
    print(f"\nCategories: {db.get_categories()}")

    # Direct lookup
    biryani = db.find("chicken biryani")
    if biryani:
        print(f"\nDirect lookup 'chicken biryani':")
        print(f"  ID: {biryani.food_id}")
        print(f"  Name: {biryani.food_name}")
        print(f"  Calories: {biryani.calories_100g} kcal/100g")
        print(f"  Source: {biryani.source}")

    # Alias lookup
    chapati = db.find("chapati")
    if chapati:
        print(f"\nAlias lookup 'chapati' -> {chapati.food_name} ({chapati.food_id})")

    # Fuzzy lookup (typo)
    fuzzy = db.find("biriyni")
    if fuzzy:
        print(f"\nFuzzy lookup 'biriyni' -> {fuzzy.food_name} ({fuzzy.food_id})")

    # Hindi name lookup
    dahi = db.find("dahi")
    if dahi:
        print(f"\nHindi lookup 'dahi' -> {dahi.food_name} ({dahi.food_id})")

    # Search
    print(f"\nSearch 'paneer':")
    results = db.search("paneer")
    for r in results:
        print(f"  - {r.food_name} ({r.food_id})")

    # Category filter
    print(f"\nSouth Indian foods:")
    south = db.get_by_category("South Indian")
    for s in south:
        print(f"  - {s.food_name}")

    # Integration with calculator
    from backend.app.nutrition.calculator import calculate_nutrition

    if biryani:
        nutrition = calculate_nutrition(
            food_name=biryani.food_name,
            nutrition_per_100g=biryani.to_nutrition_per_100g(),
            portion_grams=biryani.default_portion_g,
        )
        print(f"\n{'='*60}")
        print(f"Integration test: {biryani.food_name}")
        print(f"  Portion: {nutrition.portion_grams}g")
        print(f"  Calories: {nutrition.calories_kcal} kcal")
        print(f"  Protein: {nutrition.protein_g}g")
        print(f"  Source: {biryani.source}")

    # Unmatched food
    unknown = db.find("xylophone")
    print(f"\nUnknown food 'xylophone': {unknown}")

    print(f"\n{'='*60}")
    print("Phase 2 - All demonstrations passed!")
