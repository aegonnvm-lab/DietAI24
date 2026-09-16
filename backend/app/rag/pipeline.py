"""
RAG Pipeline — Phase 4

WHAT IT DOES:
    Ties together the embedding model, FAISS index, and food database
    into a single easy-to-use pipeline.

WHY WE NEED IT:
    Instead of manually creating an embedding model, loading an index,
    and wiring up the retriever, this pipeline handles everything.
    The analysis service just calls: pipeline.retrieve("biryani")

HOW DATA FLOWS:
    pipeline.build()  → loads database → embeds all foods → builds FAISS index
    pipeline.retrieve("query") → embed query → FAISS search → return results
"""

from __future__ import annotations

import json
import numpy as np
from pathlib import Path
from typing import List, Optional

from backend.app.nutrition.database import FoodDatabase, load_default_database
from backend.app.rag.embeddings import EmbeddingModel
from backend.app.rag.index import FAISSIndex
from backend.app.rag.retriever import FoodRetriever, RetrievalResult


class RAGPipeline:
    """
    Complete RAG pipeline for food retrieval.

    Manages:
    - Food database loading
    - Embedding generation
    - FAISS index building/loading
    - Food retrieval

    WHAT I SHOULD SEE WHEN IT WORKS:
        >>> pipeline = RAGPipeline()
        >>> pipeline.build()  # builds everything from scratch
        >>> results = pipeline.retrieve("dal fry")
        >>> print(results[0].food_record.food_name)
        Yellow Dal Tadka
    """

    def __init__(
        self,
        data_dir: Optional[str] = None,
        embedding_model_name: str = "all-MiniLM-L6-v2",
        retrieval_threshold: float = 0.3,
    ):
        self.embedding_model_name = embedding_model_name
        self.retrieval_threshold = retrieval_threshold

        # Resolve data directory
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).resolve().parent.parent.parent.parent / "data"

        # Paths for saved artifacts
        self.index_path = self.data_dir / "faiss_index.bin"
        self.food_ids_path = self.data_dir / "food_id_order.json"
        self.embeddings_path = self.data_dir / "food_embeddings.npy"

        # Components (initialized during build/load)
        self.database: Optional[FoodDatabase] = None
        self.embedding_model: Optional[EmbeddingModel] = None
        self.faiss_index: Optional[FAISSIndex] = None
        self.retriever: Optional[FoodRetriever] = None
        self.food_id_order: List[str] = []

        self._is_ready = False

    @property
    def is_ready(self) -> bool:
        """Whether the pipeline has been built/loaded and is ready to use."""
        return self._is_ready

    def build(self, save: bool = True) -> None:
        """
        Build the entire RAG pipeline from scratch.

        Steps:
        1. Load the food database
        2. Initialize the embedding model
        3. Generate embeddings for all food records
        4. Build the FAISS index
        5. Create the retriever
        6. Optionally save index to disk

        Args:
            save: Whether to save the index and embeddings to disk.
        """
        print("Building RAG pipeline...")

        # Step 1: Load database
        self.database = FoodDatabase()
        csv_path = self.data_dir / "indian_foods.csv"
        aliases_path = self.data_dir / "food_aliases.json"
        food_count = self.database.load_csv(str(csv_path))
        alias_count = self.database.load_aliases(str(aliases_path))
        print(f"  Loaded {food_count} foods, {alias_count} aliases")

        # Step 2: Initialize embedding model
        self.embedding_model = EmbeddingModel(self.embedding_model_name)

        # Step 3: Generate embeddings
        all_foods = self.database.get_all()
        self.food_id_order = [f.food_id for f in all_foods]
        texts = [f.embedding_text() for f in all_foods]

        print(f"  Generating embeddings for {len(texts)} foods...")
        embeddings = self.embedding_model.embed_batch(texts)
        print(f"  Embeddings shape: {embeddings.shape}")

        # Step 4: Build FAISS index
        self.faiss_index = FAISSIndex(dimension=embeddings.shape[1])
        self.faiss_index.build(embeddings)
        print(f"  FAISS index built with {self.faiss_index.size} vectors")

        # Step 5: Create retriever
        self.retriever = FoodRetriever(
            database=self.database,
            embedding_model=self.embedding_model,
            faiss_index=self.faiss_index,
            food_id_order=self.food_id_order,
            retrieval_threshold=self.retrieval_threshold,
        )

        # Step 6: Save to disk
        if save:
            self._save_artifacts(embeddings)

        self._is_ready = True
        print("RAG pipeline ready!")

    def load(self) -> None:
        """
        Load a previously built pipeline from disk.

        This is faster than build() because it skips embedding generation.
        """
        # Load database
        self.database = FoodDatabase()
        csv_path = self.data_dir / "indian_foods.csv"
        aliases_path = self.data_dir / "food_aliases.json"
        self.database.load_csv(str(csv_path))
        self.database.load_aliases(str(aliases_path))

        # Load food ID order
        if not self.food_ids_path.exists():
            raise FileNotFoundError(
                f"Food ID order not found at: {self.food_ids_path}\n"
                f"Run 'python scripts/build_index.py' to create it."
            )
        with open(self.food_ids_path, "r") as f:
            self.food_id_order = json.load(f)

        # Load FAISS index
        self.faiss_index = FAISSIndex()
        self.faiss_index.load(str(self.index_path))

        # Initialize and pre-warm embedding model (so first request is instant)
        self.embedding_model = EmbeddingModel(self.embedding_model_name)
        self.embedding_model._load_model()

        # Create retriever
        self.retriever = FoodRetriever(
            database=self.database,
            embedding_model=self.embedding_model,
            faiss_index=self.faiss_index,
            food_id_order=self.food_id_order,
            retrieval_threshold=self.retrieval_threshold,
        )

        self._is_ready = True

    def load_or_build(self) -> None:
        """Load from disk if available, otherwise build from scratch."""
        if self.index_path.exists() and self.food_ids_path.exists():
            try:
                self.load()
                size = self.faiss_index.size if self.faiss_index is not None else 0
                print(f"RAG pipeline loaded from disk ({size} vectors)")
                return
            except Exception as e:
                print(f"Warning: Could not load saved index ({e}). Rebuilding...")

        self.build(save=True)

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        """
        Retrieve the best matching food records for a query.

        Args:
            query: Food name or description.
            top_k: How many results to return.

        Returns:
            List of RetrievalResult sorted by similarity.
        """
        if not self._is_ready or self.retriever is None:
            raise RuntimeError(
                "RAG pipeline not initialized. "
                "Call build() or load() first."
            )
        return self.retriever.retrieve(query, top_k=top_k)

    def retrieve_best(self, query: str) -> Optional[RetrievalResult]:
        """Retrieve the single best match, or None if below threshold."""
        if not self._is_ready or self.retriever is None:
            raise RuntimeError("RAG pipeline not initialized.")
        return self.retriever.retrieve_best(query)

    def _save_artifacts(self, embeddings: np.ndarray) -> None:
        """Save index, embeddings, and food ID order to disk."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        if self.faiss_index is not None:
            self.faiss_index.save(str(self.index_path))
            print(f"  Saved FAISS index to: {self.index_path}")

        # Save food ID order (maps FAISS indices -> food_ids)
        with open(self.food_ids_path, "w") as f:
            json.dump(self.food_id_order, f, indent=2)
        print(f"  Saved food ID order to: {self.food_ids_path}")

        # Save raw embeddings (useful for debugging)
        np.save(str(self.embeddings_path), embeddings)
        print(f"  Saved embeddings to: {self.embeddings_path}")
