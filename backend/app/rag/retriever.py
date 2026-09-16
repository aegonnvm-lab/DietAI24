"""
RAG Retriever — Phase 4

WHAT IT DOES:
    Takes a food name/query and retrieves the best matching food record
    from the database using vector similarity search.

WHY WE NEED IT:
    This is the "R" in RAG — Retrieval. When the vision model says
    "I see what looks like a rice dish with meat", this module finds
    "Chicken Biryani" as the closest match in our nutrition database.

HOW DATA FLOWS:
    food query
    → embedding model → query vector
    → FAISS search → top-k indices + distances
    → map indices to food records
    → return ranked results with confidence scores

IMPORTANT PRINCIPLE:
    The retriever FINDS nutrition records. It does NOT generate them.
    The nutrition values always come from the database, never from AI.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.app.nutrition.database import FoodDatabase, FoodRecord
from backend.app.rag.embeddings import EmbeddingModel
from backend.app.rag.index import FAISSIndex


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class RetrievalResult:
    """
    A single retrieval result — one food record found by similarity search.
    """
    food_record: FoodRecord      # The matched food
    similarity_score: float       # 0.0 to 1.0 (higher = more similar)
    rank: int                     # 1 = best match, 2 = second best, etc.
    raw_distance: float           # Raw FAISS L2 distance (lower = better)

    @property
    def is_high_confidence(self) -> bool:
        """Score above 0.7 is considered high confidence."""
        return self.similarity_score >= 0.7

    @property
    def is_low_confidence(self) -> bool:
        """Score below 0.4 is considered low confidence."""
        return self.similarity_score < 0.4

    @property
    def confidence_label(self) -> str:
        """Human-readable confidence level."""
        if self.similarity_score >= 0.7:
            return "high"
        elif self.similarity_score >= 0.4:
            return "medium"
        else:
            return "low"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "food_id": str(self.food_record.food_id),
            "food_name": str(self.food_record.food_name),
            "category": str(self.food_record.category),
            "similarity_score": round(float(self.similarity_score), 3),
            "confidence": str(self.confidence_label),
            "rank": int(self.rank),
            "source": str(self.food_record.source),
        }


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------

class FoodRetriever:
    """
    Retrieves the best matching food records for a given query.

    Combines:
    1. Direct database lookup (exact/alias/fuzzy string matching)
    2. FAISS vector similarity search (semantic matching)

    The retriever tries direct lookup first (faster, more precise),
    and falls back to vector search for queries that don't match directly.

    WHAT I SHOULD SEE WHEN IT WORKS:
        >>> retriever = FoodRetriever(database, embedding_model, faiss_index, food_ids)
        >>> results = retriever.retrieve("fried rice with chicken")
        >>> print(results[0].food_record.food_name)
        Chicken Biryani
        >>> print(results[0].similarity_score)
        0.72
    """

    def __init__(
        self,
        database: FoodDatabase,
        embedding_model: EmbeddingModel,
        faiss_index: FAISSIndex,
        food_id_order: List[str],
        retrieval_threshold: float = 0.3,
    ):
        """
        Args:
            database: Loaded FoodDatabase.
            embedding_model: Initialized EmbeddingModel.
            faiss_index: Built/loaded FAISS index.
            food_id_order: List of food_ids in the same order they were indexed.
                          This maps FAISS indices → food_ids.
            retrieval_threshold: Minimum similarity score to accept a match.
        """
        self.database = database
        self.embedding_model = embedding_model
        self.faiss_index = faiss_index
        self.food_id_order = food_id_order
        self.retrieval_threshold = retrieval_threshold

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[RetrievalResult]:
        """
        Retrieve the best matching food records for a query.

        Strategy:
        1. Try direct database lookup first (exact/alias/fuzzy match)
        2. Always also do FAISS vector search
        3. Combine results, with direct match boosted to top

        Args:
            query: Food name or description to search for.
            top_k: Maximum number of results to return.

        Returns:
            List of RetrievalResult, sorted by similarity (best first).
        """
        results: List[RetrievalResult] = []

        # Step 1: Direct database lookup (Phase 2/3 normalization)
        direct_match = self.database.find(query)

        # Step 2: FAISS vector similarity search
        query_vector = self.embedding_model.embed(query)
        distances, indices = self.faiss_index.search(query_vector, top_k=top_k)

        # Convert FAISS results to RetrievalResults
        seen_ids = set()

        # If we have a direct match, add it first with boosted score
        if direct_match and direct_match.food_id in self.food_id_order:
            results.append(RetrievalResult(
                food_record=direct_match,
                similarity_score=0.95,  # Direct match gets high confidence
                rank=1,
                raw_distance=0.0,
            ))
            seen_ids.add(direct_match.food_id)

        # Add FAISS results
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < 0 or idx >= len(self.food_id_order):
                continue

            food_id = self.food_id_order[idx]
            if food_id in seen_ids:
                continue

            food_record = self.database.get_by_id(food_id)
            if food_record is None:
                continue

            similarity = float(self._distance_to_similarity(dist))

            results.append(RetrievalResult(
                food_record=food_record,
                similarity_score=similarity,
                rank=len(results) + 1,
                raw_distance=float(dist),
            ))
            seen_ids.add(food_id)

        # Re-rank by similarity
        results.sort(key=lambda r: r.similarity_score, reverse=True)
        for i, r in enumerate(results):
            r.rank = i + 1

        return results[:top_k]

    def retrieve_best(
        self,
        query: str,
    ) -> Optional[RetrievalResult]:
        """
        Retrieve the single best match for a query.

        Returns None if no match meets the confidence threshold.
        """
        results = self.retrieve(query, top_k=1)
        if not results:
            return None
        if results[0].similarity_score < self.retrieval_threshold:
            return None
        return results[0]

    @staticmethod
    def _distance_to_similarity(l2_distance: float) -> float:
        """
        Convert FAISS L2 distance to a 0-1 similarity score.

        Uses: similarity = 1 / (1 + distance)
        - Distance 0 -> similarity 1.0 (perfect match)
        - Distance 1 -> similarity 0.5
        - Distance 10 -> similarity ~0.09
        """
        return float(1.0 / (1.0 + float(l2_distance)))
