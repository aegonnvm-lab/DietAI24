"""
Embeddings Module — Phase 4

WHAT IT DOES:
    Converts text (food names/descriptions) into numerical vectors (embeddings).
    Two foods that are semantically similar will have similar vectors.

WHY WE NEED IT:
    When the vision model says "fried rice with chicken",
    we need to find "Chicken Biryani" in our database.
    Embeddings let us measure semantic similarity between texts.

HOW IT WORKS:
    Text -> sentence-transformers model -> 384-dimensional vector

IMPORTANT:
    The embedding model runs LOCALLY on your CPU.
    No API key needed. The model (~80MB) downloads once on first use.
"""

from __future__ import annotations

import numpy as np
from typing import Any, List, Optional


class EmbeddingModel:
    """
    Wrapper around sentence-transformers for generating text embeddings.

    Uses 'all-MiniLM-L6-v2' — a small, fast model that works on CPU.
    Produces 384-dimensional vectors.

    WHAT I SHOULD SEE WHEN IT WORKS:
        >>> model = EmbeddingModel()
        >>> vec = model.embed("chicken biryani")
        >>> print(vec.shape)
        (384,)
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding model.

        Args:
            model_name: Hugging Face model name. Default is a small, fast model.
                       The model downloads automatically on first use (~80MB).
        """
        self.model_name = model_name
        self._model: Optional[Any] = None

    def _load_model(self) -> Any:
        """Load the model on first use (lazy initialization)."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                print(f"Loading embedding model: {self.model_name}...")
                self._model = SentenceTransformer(self.model_name)
                dim = self._get_model_dim(self._model)
                print(f"Embedding model loaded. Dimension: {dim}")
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for embeddings.\n"
                    "Install it with: python -m pip install sentence-transformers"
                )
        return self._model

    @staticmethod
    def _get_model_dim(model: Any) -> int:
        """Retrieve embedding dimension from SentenceTransformer without deprecation warnings."""
        if hasattr(model, "get_embedding_dimension"):
            return int(model.get_embedding_dimension())
        elif hasattr(model, "get_sentence_embedding_dimension"):
            return int(model.get_sentence_embedding_dimension())
        return 384

    def embed(self, text: str) -> np.ndarray:
        """
        Convert a single text string into a vector.

        Args:
            text: Any text (food name, description, query).

        Returns:
            numpy array of shape (384,) — the embedding vector.
        """
        model = self._load_model()
        vector = model.encode([text], show_progress_bar=False)
        return np.array(vector[0], dtype=np.float32)

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Convert multiple texts into vectors efficiently.

        Args:
            texts: List of text strings.
            batch_size: How many texts to process at once.

        Returns:
            numpy array of shape (len(texts), 384).
        """
        model = self._load_model()
        vectors = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
        )
        return np.array(vectors, dtype=np.float32)

    @property
    def dimension(self) -> int:
        """Return the embedding dimension (384 for MiniLM)."""
        model = self._load_model()
        return self._get_model_dim(model)
