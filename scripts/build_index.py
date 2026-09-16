"""
Build FAISS Index Script

Run this script to build the embedding vectors and FAISS index
from the food database.

Usage:
    cd indian-food-calorie-estimator
    python scripts/build_index.py

What it does:
    1. Loads all food records from data/indian_foods.csv
    2. Generates embedding vectors using sentence-transformers
    3. Builds a FAISS index for fast similarity search
    4. Saves everything to data/ directory

Output files:
    data/faiss_index.bin      — the FAISS index
    data/food_embeddings.npy  — the raw embedding vectors
    data/food_id_order.json   — maps FAISS indices to food_ids
"""

import sys
from pathlib import Path

# Add project root to path so imports work
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from backend.app.rag.pipeline import RAGPipeline


def main():
    print("=" * 60)
    print("Building FAISS Index for Indian Food Database")
    print("=" * 60)

    pipeline = RAGPipeline()
    pipeline.build(save=True)

    count = pipeline.faiss_index.size if pipeline.faiss_index else 0
    print(f"  Foods indexed: {count}")
    print(f"  Index file: data/faiss_index.bin")
    print(f"  Embeddings: data/food_embeddings.npy")
    print(f"  ID mapping: data/food_id_order.json")

    # Quick test
    print(f"\n{'='*60}")
    print("Quick retrieval test:")
    print("=" * 60)

    test_queries = [
        "chicken biryani",
        "roti",
        "spinach with cheese",
        "fried snack with potato",
        "sweet milk dessert",
        "south indian pancake",
    ]

    for query in test_queries:
        results = pipeline.retrieve(query, top_k=3)
        if results:
            best = results[0]
            print(f"\n  Query: '{query}'")
            print(f"  Best match: {best.food_record.food_name} "
                  f"(score: {best.similarity_score:.3f}, "
                  f"confidence: {best.confidence_label})")
            if len(results) > 1:
                alt = results[1]
                print(f"  2nd match:  {alt.food_record.food_name} "
                      f"(score: {alt.similarity_score:.3f})")
        else:
            print(f"\n  Query: '{query}' -> No match found")

    print(f"\n{'='*60}")
    print("Build complete!")


if __name__ == "__main__":
    main()
