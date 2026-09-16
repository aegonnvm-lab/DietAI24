"""
Strict Food Matcher & Anti-False-Positive Engine — Phase 4 Upgrade

CORE PRINCIPLE:
    SEPARATE:
    1. Visual Recognition
    2. Food Normalization
    3. Nutrition Retrieval
    4. Deterministic Calculation

NEVER DO:
    nearest_vector = chosen_food
    always accept nearest_vector

If an omelette is detected, it must NEVER resolve to Yellow Dal Tadka
simply because their embeddings happen to have positive cosine similarity.

If a food cannot be confidently matched to a database record, the system returns
'LOW_CONFIDENCE' or 'NUTRITION_UNAVAILABLE' rather than guessing a wrong food.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from backend.app.nutrition.database import FoodDatabase, FoodRecord, normalize_text
from backend.app.rag.retriever import FoodRetriever, RetrievalResult


class MatchStatus(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    MEDIUM_CONFIDENCE = "MEDIUM_CONFIDENCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    NUTRITION_UNAVAILABLE = "NUTRITION_UNAVAILABLE"
    REJECTED_CATEGORY_MISMATCH = "REJECTED_CATEGORY_MISMATCH"


@dataclass
class StrictMatchResult:
    """Outcome of strict anti-false-positive food matching."""
    status: MatchStatus
    food_record: Optional[FoodRecord]
    confidence_score: float
    query: str
    explanation: str
    top_candidates: List[Dict[str, Any]] = field(default_factory=list)
    rejected_candidates: List[Dict[str, Any]] = field(default_factory=list)
    needs_user_review: bool = False

    @property
    def is_accepted(self) -> bool:
        return self.status in (MatchStatus.EXACT_MATCH, MatchStatus.HIGH_CONFIDENCE, MatchStatus.MEDIUM_CONFIDENCE) and self.food_record is not None


# Incompatible category pairings to block absurd vector substitutions
CATEGORY_INCOMPATIBILITIES: Dict[str, Set[str]] = {
    "egg": {"Dals and Lentils", "Breads and Roti", "Sweets and Desserts", "Beverages"},
    "omelette": {"Dals and Lentils", "Breads and Roti", "Sweets and Desserts", "Beverages", "Rice Dishes"},
    "dal": {"Eggs and Poultry", "Breads and Roti", "Beverages", "Fruits", "Sweets and Desserts"},
    "lentil": {"Eggs and Poultry", "Breads and Roti", "Beverages", "Fruits"},
    "roti": {"Dals and Lentils", "Curries and Gravies", "Beverages", "Dairy", "Soups"},
    "rice": {"Beverages", "Breads and Roti", "Eggs and Poultry"},
    "chai": {"Curries and Gravies", "Rice Dishes", "Dals and Lentils", "Vegetable Dishes"},
    "coffee": {"Curries and Gravies", "Rice Dishes", "Dals and Lentils", "Vegetable Dishes"},
    "fruit": {"Curries and Gravies", "Dals and Lentils", "Breads and Roti", "Fried Snacks"},
}


class StrictFoodMatcher:
    """
    Guards retrieval against false-positive substitutions.
    Enforces multi-tier confidence gating, alias normalization, and category checks.
    """

    def __init__(
        self,
        retriever: FoodRetriever,
        database: FoodDatabase,
        high_threshold: float = 0.72,
        medium_threshold: float = 0.50,
        min_visual_confidence: float = 0.40,
    ):
        self.retriever = retriever
        self.database = database
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold
        self.min_visual_confidence = min_visual_confidence

    def match(
        self,
        query: str,
        visual_confidence: float = 1.0,
        top_k: int = 5,
    ) -> StrictMatchResult:
        """
        Evaluate candidate matches with strict acceptance criteria.

        Args:
            query: Visual detection label (e.g. "Omelette", "masala dosa", "unknown dish")
            visual_confidence: Confidence from the vision stage (0.0 to 1.0)
            top_k: Number of RAG candidates to inspect
        """
        clean_query = query.strip()
        lower_query = clean_query.lower()

        # Step 0: Uncertainty check from visual stage
        if visual_confidence < self.min_visual_confidence or any(
            bad in lower_query for bad in ["unknown", "ambiguous", "unclear", "low-confidence"]
        ):
            return StrictMatchResult(
                status=MatchStatus.LOW_CONFIDENCE,
                food_record=None,
                confidence_score=visual_confidence,
                query=clean_query,
                explanation=f"Visual detection uncertainty too high ({visual_confidence:.2f}). Please verify or specify the food name.",
                needs_user_review=True,
            )

        # Step 1: Direct Alias / Lexical Normalization
        norm_query = normalize_text(clean_query)
        if norm_query in self.database._name_index:
            canonical_id = self.database._name_index[norm_query]
            record = self.database.get_by_id(canonical_id)
            if record:
                return StrictMatchResult(
                    status=MatchStatus.EXACT_MATCH,
                    food_record=record,
                    confidence_score=1.0,
                    query=clean_query,
                    explanation=f"Exact match to database record '{record.food_name}'",
                    top_candidates=[{"food": record.food_name, "score": 1.0, "status": "EXACT_MATCH"}],
                    needs_user_review=False,
                )

        # Direct exact or fuzzy match check
        direct_match = self.database.find(clean_query)
        if direct_match and normalize_text(direct_match.food_name) == norm_query:
            return StrictMatchResult(
                status=MatchStatus.EXACT_MATCH,
                food_record=direct_match,
                confidence_score=1.0,
                query=clean_query,
                explanation=f"Exact canonical match to '{direct_match.food_name}'",
                top_candidates=[{"food": direct_match.food_name, "score": 1.0, "status": "EXACT_CANONICAL"}],
                needs_user_review=False,
            )

        # Step 2: Vector Similarity Retrieval
        raw_candidates: List[RetrievalResult] = self.retriever.retrieve(clean_query, top_k=top_k)

        if not raw_candidates:
            return StrictMatchResult(
                status=MatchStatus.NUTRITION_UNAVAILABLE,
                food_record=None,
                confidence_score=0.0,
                query=clean_query,
                explanation=f"'{clean_query}' identified visually, but no nutrition record was found in the database.",
                needs_user_review=True,
            )

        candidate_summaries = []
        rejected_summaries = []

        best_candidate = raw_candidates[0]
        score = float(best_candidate.similarity_score)

        for c in raw_candidates:
            summary = {
                "food_id": c.food_record.food_id,
                "name": c.food_record.food_name,
                "category": c.food_record.category,
                "similarity_score": round(float(c.similarity_score), 3),
            }
            candidate_summaries.append(summary)

        # Step 3: Check Category Incompatibility Safeguards
        # e.g., if query is "omelette", reject any match from "Dals and Lentils"
        for kw, blocked_categories in CATEGORY_INCOMPATIBILITIES.items():
            if kw in lower_query:
                if best_candidate.food_record.category in blocked_categories:
                    rejected_summaries.append({
                        "food": best_candidate.food_record.food_name,
                        "category": best_candidate.food_record.category,
                        "reason": f"Category mismatch: '{kw}' cannot resolve to '{best_candidate.food_record.category}'",
                        "score": score,
                    })
                    return StrictMatchResult(
                        status=MatchStatus.REJECTED_CATEGORY_MISMATCH,
                        food_record=None,
                        confidence_score=score,
                        query=clean_query,
                        explanation=(
                            f"Rejected nearest match '{best_candidate.food_record.food_name}' ({best_candidate.food_record.category}). "
                            f"An egg or distinct food must not be mapped to an incompatible category."
                        ),
                        top_candidates=candidate_summaries,
                        rejected_candidates=rejected_summaries,
                        needs_user_review=True,
                    )

        # Step 4: Strict Threshold Gating
        if score >= self.high_threshold:
            return StrictMatchResult(
                status=MatchStatus.HIGH_CONFIDENCE,
                food_record=best_candidate.food_record,
                confidence_score=score,
                query=clean_query,
                explanation=f"High-confidence semantic match to '{best_candidate.food_record.food_name}' (score: {score:.3f})",
                top_candidates=candidate_summaries,
                needs_user_review=False,
            )
        elif score >= self.medium_threshold:
            return StrictMatchResult(
                status=MatchStatus.MEDIUM_CONFIDENCE,
                food_record=best_candidate.food_record,
                confidence_score=score,
                query=clean_query,
                explanation=f"Moderate-confidence match to '{best_candidate.food_record.food_name}' (score: {score:.3f}). Review suggested.",
                top_candidates=candidate_summaries,
                needs_user_review=True,
            )
        else:
            # Score is below minimum acceptable threshold (< 0.50)
            # NEVER force a nearest vector match!
            rejected_summaries.append({
                "food": best_candidate.food_record.food_name,
                "score": score,
                "reason": f"Similarity score {score:.3f} below minimum threshold ({self.medium_threshold})",
            })
            return StrictMatchResult(
                status=MatchStatus.NUTRITION_UNAVAILABLE,
                food_record=None,
                confidence_score=score,
                query=clean_query,
                explanation=(
                    f"'{clean_query}' identified visually, but best database match "
                    f"'{best_candidate.food_record.food_name}' scored only {score:.3f} (< {self.medium_threshold}). "
                    f"Nutrition record unavailable."
                ),
                top_candidates=candidate_summaries,
                rejected_candidates=rejected_summaries,
                needs_user_review=True,
            )
