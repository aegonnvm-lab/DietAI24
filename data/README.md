# Indian Food Nutrition Dataset

## Overview

This directory contains the nutrition data used by the Indian Food Calorie Estimation system.

## Files

| File | Purpose |
|------|---------|
| `indian_foods.csv` | Primary nutrition dataset — 50 Indian food items |
| `food_aliases.json` | Maps common names/spellings to standardized food_ids |
| `indian_food_nutrition.json` | Legacy JSON export (from earlier prototype) |

## Dataset Status

> **IMPORTANT: DEMO / DEVELOPMENT DATA**
>
> The nutrition values in this dataset are **approximate values** compiled
> for development and demonstration purposes. They have NOT been verified
> against an official Indian nutrition database.
>
> For research or clinical use, these values MUST be replaced with data from
> verified sources such as:
> - Indian Food Composition Tables (IFCT, NIN Hyderabad)
> - ICMR-NIN Nutrient Requirements
> - Published peer-reviewed food composition data

## CSV Column Definitions

| Column | Type | Description |
|--------|------|-------------|
| `food_id` | String | Unique identifier (e.g., IF001) |
| `food_name` | String | Standardized English food name |
| `aliases` | String | Comma-separated alternative names |
| `category` | String | Food category |
| `calories_100g` | Float | Energy per 100g (kcal) |
| `protein_100g` | Float | Protein per 100g (g) |
| `carbs_100g` | Float | Carbohydrates per 100g (g) |
| `fat_100g` | Float | Fat per 100g (g) |
| `fiber_100g` | Float | Dietary fiber per 100g (g) |
| `default_portion_g` | Float | Default portion size estimate (g) |
| `source` | String | Data source indicator |
| `notes` | String | Description of the food item |

## Categories

- Rice Dishes
- Breads
- Dals and Lentils
- Curries
- South Indian
- Breakfast
- Snacks
- Dairy
- Beverages
- Sweets
- Vegetables
- Condiments

## How to Update / Replace Data

1. Edit `indian_foods.csv` directly (any spreadsheet application works)
2. Keep the same column structure
3. Ensure every `food_id` is unique
4. Update `food_aliases.json` if adding new foods
5. Run `python scripts/build_index.py` to rebuild the FAISS index

## How to Rebuild Embeddings

After modifying the CSV:

```bash
cd indian-food-calorie-estimator
python scripts/build_embeddings.py
python scripts/build_index.py
```

This regenerates the vector embeddings and FAISS index used for
food retrieval (RAG).
