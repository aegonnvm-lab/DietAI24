"""
FAISS Index Module — Phase 4

WHAT IT DOES:
    Builds and manages a FAISS index — a fast search structure for finding
    the most similar vectors (and therefore the most similar food records).

WHY WE NEED IT:
    With 50+ food records, we could do brute-force comparison.
    But FAISS is designed for this and scales to thousands of records.
    It also establishes the architecture for future dataset growth.

HOW IT WORKS:
    1. Build: take all food embeddings -> create FAISS index -> save to disk
    2. Search: take a query embedding -> find top-k nearest neighbors -> return results
"""

from __future__ import annotations

import faiss
import numpy as np
from pathlib import Path
from typing import Any, Optional, Tuple


class FAISSIndex:
    """
    Manages a FAISS index for food embedding similarity search.

    WHAT I SHOULD SEE WHEN IT WORKS:
        >>> index = FAISSIndex(dimension=384)
        >>> index.build(embeddings)  # add food vectors
        >>> distances, indices = index.search(query_vector, top_k=5)
        >>> print(indices)  # [3, 7, 1, ...]  (IDs of most similar foods)
    """

    def __init__(self, dimension: int = 384):
        """
        Initialize FAISS index.

        Args:
            dimension: Vector dimension (384 for MiniLM-L6-v2).
        """
        self.dimension = dimension
        self._index: Optional[Any] = None

    def build(self, embeddings: np.ndarray) -> None:
        """
        Build a new FAISS index from a matrix of embeddings.

        Args:
            embeddings: numpy array of shape (n_foods, dimension).
                       Each row is one food's embedding vector.
        """
        if embeddings.ndim != 2 or embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Expected embeddings of shape (n, {self.dimension}), "
                f"got {embeddings.shape}"
            )

        # Use L2 (Euclidean distance) index — simple and effective
        index = faiss.IndexFlatL2(self.dimension)
        index.add(embeddings.astype(np.float32))
        self._index = index

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for the top-k most similar vectors.

        Args:
            query_vector: The query embedding (shape: (dimension,) or (1, dimension)).
            top_k: How many results to return.

        Returns:
            Tuple of (distances, indices):
            - distances: shape (1, top_k) — lower = more similar
            - indices: shape (1, top_k) — positions in the original embeddings array
        """
        if self._index is None:
            raise RuntimeError(
                "FAISS index not built yet. "
                "Run build() or load() first."
            )

        # Reshape to 2D if needed
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)

        query_vector = query_vector.astype(np.float32)

        # Clamp top_k to available items
        actual_k = min(top_k, self._index.ntotal)

        distances, indices = self._index.search(query_vector, actual_k)
        return distances, indices

    def save(self, path: str) -> None:
        """Save the FAISS index to a file."""
        if self._index is None:
            raise RuntimeError("No index to save. Build it first.")

        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, path)

    def load(self, path: str) -> None:
        """Load a FAISS index from a file."""
        if not Path(path).exists():
            raise FileNotFoundError(
                f"FAISS index not found at: {path}\n"
                f"Run 'python scripts/build_index.py' to create it."
            )

        index = faiss.read_index(path)
        self._index = index
        self.dimension = index.d

    @property
    def size(self) -> int:
        """Number of vectors in the index."""
        if self._index is None:
            return 0
        return int(self._index.ntotal)
