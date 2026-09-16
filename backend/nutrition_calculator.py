"""
Indian Food Nutrition & Calorie Calculator

This module provides data models, nutritional calculations, serving size conversions,
and meal aggregation specifically tailored for Indian cuisine.
"""

from __future__ import annotations

import difflib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class NutritionalInfo:
    """Represents nutritional values for a given quantity of food."""
    calories: float  # in kcal
    protein: float  # in grams
    carbohydrates: float  # in grams
    fat: float  # in grams
    fiber: float = 0.0  # in grams
    serving_weight_g: float = 100.0  # weight in grams
    serving_unit: str = "g"
    serving_count: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def round_values(self, decimals: int = 1) -> NutritionalInfo:
        return NutritionalInfo(
            calories=round(self.calories, decimals),
            protein=round(self.protein, decimals),
            carbohydrates=round(self.carbohydrates, decimals),
            fat=round(self.fat, decimals),
            fiber=round(self.fiber, decimals),
            serving_weight_g=round(self.serving_weight_g, decimals),
            serving_unit=self.serving_unit,
            serving_count=round(self.serving_count, decimals),
        )


@dataclass
class FoodItem:
    """Represents an Indian food item with standard nutritional values per 100g."""
    id: str
    name: str
    hindi_name: Optional[str] = None
    category: str = "General"  # e.g., Curries, Breads, Rice, Snacks, Sweets, South Indian, Dals
    calories_per_100g: float = 0.0
    protein_per_100g: float = 0.0
    carbs_per_100g: float = 0.0
    fat_per_100g: float = 0.0
    fiber_per_100g: float = 0.0
    # Serving units mapping to equivalent weight in grams:
    # e.g. {"piece": 40.0, "katori": 150.0, "plate": 300.0}
    serving_conversions: Dict[str, float] = field(default_factory=dict)
    description: str = ""

    def calculate_nutrition(self, quantity: float, unit: str = "g") -> NutritionalInfo:
        """Calculate nutritional values for a specific quantity and unit."""
        unit_lower = unit.lower().strip()
        weight_g = 0.0

        if unit_lower in ("g", "gram", "grams"):
            weight_g = quantity
        elif unit_lower in ("kg", "kilogram", "kilograms"):
            weight_g = quantity * 1000.0
        elif unit_lower in self.serving_conversions:
            weight_g = quantity * self.serving_conversions[unit_lower]
        elif (
            unit_lower.rstrip("s") in self.serving_conversions
        ):  # handle simple plurals like 'pieces' -> 'piece'
            weight_g = quantity * self.serving_conversions[unit_lower.rstrip("s")]
        else:
            # Fallback if standard unit is not recognized
            available_units = ["g", "kg"] + list(self.serving_conversions.keys())
            raise ValueError(
                f"Unknown unit '{unit}' for '{self.name}'. "
                f"Available units: {', '.join(available_units)}"
            )

        factor = weight_g / 100.0

        return NutritionalInfo(
            calories=self.calories_per_100g * factor,
            protein=self.protein_per_100g * factor,
            carbohydrates=self.carbs_per_100g * factor,
            fat=self.fat_per_100g * factor,
            fiber=self.fiber_per_100g * factor,
            serving_weight_g=weight_g,
            serving_unit=unit,
            serving_count=quantity,
        )


@dataclass
class MealItemInput:
    food_name_or_id: str
    quantity: float
    unit: str = "g"


@dataclass
class MealItemResult:
    food_id: str
    food_name: str
    category: str
    quantity: float
    unit: str
    weight_g: float
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: float


@dataclass
class MealSummary:
    """Summary of complete meal's nutritional content."""
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    total_fiber: float
    total_weight_g: float
    macro_percentages: Dict[str, float]  # % calories from protein, carbs, fat
    items: List[MealItemResult]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Default built-in Indian food database with verified approximate values per 100g
DEFAULT_INDIAN_FOODS: List[Dict[str, Any]] = [
    # Breads / Roti
    {
        "id": "roti_chapati",
        "name": "Roti (Chapati / Phulka)",
        "hindi_name": "रोटी / फुल्का",
        "category": "Breads",
        "calories_per_100g": 297.0,
        "protein_per_100g": 9.2,
        "carbs_per_100g": 55.8,
        "fat_per_100g": 3.7,
        "fiber_per_100g": 10.7,
        "serving_conversions": {"piece": 35.0, "roti": 35.0, "serving": 70.0},
        "description": "Whole wheat flatbread cooked without oil on a tawa.",
    },
    {
        "id": "paratha_plain",
        "name": "Plain Tawa Paratha",
        "hindi_name": "सादा परांठा",
        "category": "Breads",
        "calories_per_100g": 326.0,
        "protein_per_100g": 7.5,
        "carbs_per_100g": 48.0,
        "fat_per_100g": 11.5,
        "fiber_per_100g": 6.8,
        "serving_conversions": {"piece": 60.0, "paratha": 60.0},
        "description": "Layered whole wheat flatbread cooked with ghee/oil.",
    },
    {
        "id": "aloo_paratha",
        "name": "Aloo Paratha",
        "hindi_name": "आलू परांठा",
        "category": "Breads",
        "calories_per_100g": 240.0,
        "protein_per_100g": 5.4,
        "carbs_per_100g": 36.0,
        "fat_per_100g": 8.5,
        "fiber_per_100g": 4.2,
        "serving_conversions": {"piece": 110.0, "paratha": 110.0},
        "description": "Stuffed spiced potato whole wheat flatbread.",
    },
    {
        "id": "butter_naan",
        "name": "Butter Naan",
        "hindi_name": "बटर नान",
        "category": "Breads",
        "calories_per_100g": 310.0,
        "protein_per_100g": 8.0,
        "carbs_per_100g": 49.0,
        "fat_per_100g": 9.5,
        "fiber_per_100g": 2.5,
        "serving_conversions": {"piece": 90.0, "naan": 90.0},
        "description": "Tandoor baked refined flour bread brushed with butter.",
    },
    {
        "id": "poori",
        "name": "Poori",
        "hindi_name": "पूरी",
        "category": "Breads",
        "calories_per_100g": 380.0,
        "protein_per_100g": 7.0,
        "carbs_per_100g": 47.0,
        "fat_per_100g": 18.5,
        "fiber_per_100g": 3.8,
        "serving_conversions": {"piece": 30.0, "poori": 30.0},
        "description": "Deep-fried puffed unleavened whole wheat bread.",
    },
    # Rice Dishes
    {
        "id": "steamed_white_rice",
        "name": "Steamed White Rice",
        "hindi_name": "उबले चावल",
        "category": "Rice",
        "calories_per_100g": 130.0,
        "protein_per_100g": 2.7,
        "carbs_per_100g": 28.2,
        "fat_per_100g": 0.3,
        "fiber_per_100g": 0.4,
        "serving_conversions": {"katori": 150.0, "cup": 160.0, "plate": 250.0},
        "description": "Cooked plain white rice.",
    },
    {
        "id": "jeera_rice",
        "name": "Jeera Rice",
        "hindi_name": "जीरा राइस",
        "category": "Rice",
        "calories_per_100g": 165.0,
        "protein_per_100g": 2.9,
        "carbs_per_100g": 29.5,
        "fat_per_100g": 4.0,
        "fiber_per_100g": 0.8,
        "serving_conversions": {"katori": 150.0, "cup": 160.0, "plate": 250.0},
        "description": "Basmati rice tempered with cumin seeds and ghee.",
    },
    {
        "id": "chicken_biryani",
        "name": "Chicken Biryani",
        "hindi_name": "चिकन बिरयानी",
        "category": "Rice",
        "calories_per_100g": 180.0,
        "protein_per_100g": 9.5,
        "carbs_per_100g": 22.0,
        "fat_per_100g": 6.2,
        "fiber_per_100g": 1.2,
        "serving_conversions": {"plate": 350.0, "cup": 180.0, "katori": 150.0},
        "description": "Fragrant basmati rice layered with spiced marinated chicken.",
    },
    {
        "id": "veg_biryani",
        "name": "Vegetable Biryani / Pulao",
        "hindi_name": "वेज बिरयानी / पुलाव",
        "category": "Rice",
        "calories_per_100g": 145.0,
        "protein_per_100g": 3.8,
        "carbs_per_100g": 24.5,
        "fat_per_100g": 3.8,
        "fiber_per_100g": 2.2,
        "serving_conversions": {"plate": 300.0, "cup": 170.0, "katori": 150.0},
        "description": "Rice cooked with mixed vegetables, whole spices, and aromatics.",
    },
    # Dals & Lentils
    {
        "id": "dal_tadka",
        "name": "Yellow Dal Tadka",
        "hindi_name": "दाल तड़का",
        "category": "Dals",
        "calories_per_100g": 105.0,
        "protein_per_100g": 5.8,
        "carbs_per_100g": 13.5,
        "fat_per_100g": 3.2,
        "fiber_per_100g": 3.0,
        "serving_conversions": {"katori": 150.0, "cup": 200.0, "bowl": 220.0},
        "description": "Yellow toor dal cooked and tempered with cumin, garlic, and ghee.",
    },
    {
        "id": "dal_makhani",
        "name": "Dal Makhani",
        "hindi_name": "दाल मखनी",
        "category": "Dals",
        "calories_per_100g": 165.0,
        "protein_per_100g": 6.2,
        "carbs_per_100g": 15.0,
        "fat_per_100g": 9.0,
        "fiber_per_100g": 4.5,
        "serving_conversions": {"katori": 150.0, "cup": 200.0, "bowl": 220.0},
        "description": "Slow cooked black lentils and kidney beans with butter and cream.",
    },
    {
        "id": "rajma_curry",
        "name": "Rajma Masala (Kidney Beans Curry)",
        "hindi_name": "राजमा मसाला",
        "category": "Dals",
        "calories_per_100g": 125.0,
        "protein_per_100g": 6.8,
        "carbs_per_100g": 17.5,
        "fat_per_100g": 3.4,
        "fiber_per_100g": 5.2,
        "serving_conversions": {"katori": 150.0, "cup": 200.0, "bowl": 220.0},
        "description": "Red kidney beans simmered in a spiced onion-tomato gravy.",
    },
    {
        "id": "chole_chana_masala",
        "name": "Chole / Chana Masala",
        "hindi_name": "छोले / चना मसाला",
        "category": "Curries",
        "calories_per_100g": 155.0,
        "protein_per_100g": 7.2,
        "carbs_per_100g": 21.0,
        "fat_per_100g": 4.8,
        "fiber_per_100g": 6.0,
        "serving_conversions": {"katori": 150.0, "cup": 200.0, "bowl": 220.0},
        "description": "Chickpeas cooked in a tangy, robust spiced onion-tomato gravy.",
    },
    # Curries (Veg & Non-Veg)
    {
        "id": "paneer_butter_masala",
        "name": "Paneer Butter Masala",
        "hindi_name": "पनीर बटर मसाला",
        "category": "Curries",
        "calories_per_100g": 225.0,
        "protein_per_100g": 8.5,
        "carbs_per_100g": 9.5,
        "fat_per_100g": 17.5,
        "fiber_per_100g": 1.8,
        "serving_conversions": {"katori": 150.0, "cup": 200.0, "bowl": 220.0},
        "description": "Cottage cheese cubes cooked in a rich, buttery tomato cream gravy.",
    },
    {
        "id": "palak_paneer",
        "name": "Palak Paneer",
        "hindi_name": "पालक पनीर",
        "category": "Curries",
        "calories_per_100g": 145.0,
        "protein_per_100g": 8.2,
        "carbs_per_100g": 5.4,
        "fat_per_100g": 10.5,
        "fiber_per_100g": 3.0,
        "serving_conversions": {"katori": 150.0, "cup": 200.0, "bowl": 220.0},
        "description": "Paneer cubes in a spiced puree of fresh spinach greens.",
    },
    {
        "id": "butter_chicken",
        "name": "Butter Chicken (Murgh Makhani)",
        "hindi_name": "बटर चिकन",
        "category": "Curries",
        "calories_per_100g": 210.0,
        "protein_per_100g": 13.5,
        "carbs_per_100g": 6.5,
        "fat_per_100g": 14.5,
        "fiber_per_100g": 1.2,
        "serving_conversions": {"katori": 150.0, "cup": 200.0, "bowl": 220.0},
        "description": "Tender chicken cooked in a mild spiced tomato, butter, and cream sauce.",
    },
    {
        "id": "aloo_gobi",
        "name": "Aloo Gobi",
        "hindi_name": "आलू गोभी",
        "category": "Curries",
        "calories_per_100g": 110.0,
        "protein_per_100g": 2.8,
        "carbs_per_100g": 15.2,
        "fat_per_100g": 4.5,
        "fiber_per_100g": 3.5,
        "serving_conversions": {"katori": 140.0, "cup": 180.0, "bowl": 200.0},
        "description": "Dry curry of potatoes and cauliflower sautéed with turmeric and spices.",
    },
    {
        "id": "bhindi_masala",
        "name": "Bhindi Masala (Okra)",
        "hindi_name": "भिंडी मसाला",
        "category": "Curries",
        "calories_per_100g": 98.0,
        "protein_per_100g": 2.4,
        "carbs_per_100g": 10.5,
        "fat_per_100g": 5.2,
        "fiber_per_100g": 4.1,
        "serving_conversions": {"katori": 130.0, "cup": 170.0, "bowl": 190.0},
        "description": "Spiced stir-fried okra with onions and tomatoes.",
    },
    {
        "id": "egg_curry",
        "name": "Egg Curry",
        "hindi_name": "अंडा करी",
        "category": "Curries",
        "calories_per_100g": 135.0,
        "protein_per_100g": 9.2,
        "carbs_per_100g": 4.5,
        "fat_per_100g": 9.0,
        "fiber_per_100g": 1.0,
        "serving_conversions": {"serving": 180.0, "bowl": 200.0, "piece_egg_with_gravy": 100.0},
        "description": "Hard-boiled eggs simmered in spicy onion-tomato gravy.",
    },
    # South Indian
    {
        "id": "idli",
        "name": "Idli",
        "hindi_name": "इडली",
        "category": "South Indian",
        "calories_per_100g": 132.0,
        "protein_per_100g": 3.9,
        "carbs_per_100g": 27.5,
        "fat_per_100g": 0.6,
        "fiber_per_100g": 1.8,
        "serving_conversions": {"piece": 50.0, "idli": 50.0, "plate": 100.0},
        "description": "Steamed savory fermented rice and black lentil cakes.",
    },
    {
        "id": "plain_dosa",
        "name": "Plain Dosa (Sada Dosa)",
        "hindi_name": "सादा डोसा",
        "category": "South Indian",
        "calories_per_100g": 168.0,
        "protein_per_100g": 4.2,
        "carbs_per_100g": 31.0,
        "fat_per_100g": 3.0,
        "fiber_per_100g": 1.5,
        "serving_conversions": {"piece": 100.0, "dosa": 100.0},
        "description": "Crisp fermented rice and lentil crepe.",
    },
    {
        "id": "masala_dosa",
        "name": "Masala Dosa",
        "hindi_name": "मसाला डोसा",
        "category": "South Indian",
        "calories_per_100g": 185.0,
        "protein_per_100g": 4.5,
        "carbs_per_100g": 30.5,
        "fat_per_100g": 5.2,
        "fiber_per_100g": 2.4,
        "serving_conversions": {"piece": 180.0, "dosa": 180.0},
        "description": "Crispy dosa folded around spiced mashed potato filling.",
    },
    {
        "id": "medu_vada",
        "name": "Medu Vada",
        "hindi_name": "मेदू वड़ा",
        "category": "South Indian",
        "calories_per_100g": 290.0,
        "protein_per_100g": 8.5,
        "carbs_per_100g": 34.0,
        "fat_per_100g": 13.5,
        "fiber_per_100g": 4.0,
        "serving_conversions": {"piece": 50.0, "vada": 50.0},
        "description": "Crispy deep-fried savory doughnut made from urad dal batter.",
    },
    {
        "id": "sambar",
        "name": "Sambar",
        "hindi_name": "सांभर",
        "category": "South Indian",
        "calories_per_100g": 65.0,
        "protein_per_100g": 2.8,
        "carbs_per_100g": 9.8,
        "fat_per_100g": 1.6,
        "fiber_per_100g": 2.2,
        "serving_conversions": {"katori": 150.0, "cup": 200.0, "bowl": 220.0},
        "description": "Lentil stew cooked with tamarind, vegetables, and aromatic sambar powder.",
    },
    {
        "id": "coconut_chutney",
        "name": "Coconut Chutney",
        "hindi_name": "नारियल की चटनी",
        "category": "South Indian",
        "calories_per_100g": 210.0,
        "protein_per_100g": 2.9,
        "carbs_per_100g": 8.5,
        "fat_per_100g": 19.0,
        "fiber_per_100g": 4.5,
        "serving_conversions": {"tbsp": 15.0, "serving": 30.0, "katori": 60.0},
        "description": "Ground fresh coconut, green chilies, roasted chana dal, tempered with mustard.",
    },
    # Breakfast & Snacks
    {
        "id": "poha",
        "name": "Poha",
        "hindi_name": "पोहा",
        "category": "Snacks",
        "calories_per_100g": 160.0,
        "protein_per_100g": 3.2,
        "carbs_per_100g": 27.5,
        "fat_per_100g": 4.2,
        "fiber_per_100g": 2.0,
        "serving_conversions": {"katori": 140.0, "plate": 200.0, "cup": 150.0},
        "description": "Flattened rice tempered with mustard, turmeric, peanuts, and curry leaves.",
    },
    {
        "id": "upma",
        "name": "Rava Upma",
        "hindi_name": "रवा उपमा",
        "category": "Snacks",
        "calories_per_100g": 155.0,
        "protein_per_100g": 3.8,
        "carbs_per_100g": 24.0,
        "fat_per_100g": 4.8,
        "fiber_per_100g": 1.6,
        "serving_conversions": {"katori": 140.0, "plate": 200.0, "cup": 150.0},
        "description": "Roasted semolina porridge tempered with spices and vegetables.",
    },
    {
        "id": "samosa",
        "name": "Samosa",
        "hindi_name": "समोसा",
        "category": "Snacks",
        "calories_per_100g": 310.0,
        "protein_per_100g": 5.2,
        "carbs_per_100g": 35.0,
        "fat_per_100g": 16.5,
        "fiber_per_100g": 2.5,
        "serving_conversions": {"piece": 85.0, "samosa": 85.0},
        "description": "Crispy fried pastry cone stuffed with spiced potatoes and peas.",
    },
    {
        "id": "pav_bhaji",
        "name": "Pav Bhaji (Bhaji only)",
        "hindi_name": "पाव भाजी (भाजी)",
        "category": "Snacks",
        "calories_per_100g": 130.0,
        "protein_per_100g": 2.8,
        "carbs_per_100g": 16.5,
        "fat_per_100g": 6.0,
        "fiber_per_100g": 3.5,
        "serving_conversions": {"katori": 150.0, "plate": 250.0},
        "description": "Spiced mashed vegetable curry cooked with butter.",
    },
    {
        "id": "pav",
        "name": "Pav (Bread bun)",
        "hindi_name": "पाव",
        "category": "Breads",
        "calories_per_100g": 270.0,
        "protein_per_100g": 8.0,
        "carbs_per_100g": 54.0,
        "fat_per_100g": 2.2,
        "fiber_per_100g": 2.0,
        "serving_conversions": {"piece": 40.0, "pav": 40.0, "pair": 80.0},
        "description": "Indian style soft white bread bun.",
    },
    {
        "id": "bhature",
        "name": "Bhature",
        "hindi_name": "भटूरा",
        "category": "Breads",
        "calories_per_100g": 360.0,
        "protein_per_100g": 6.8,
        "carbs_per_100g": 46.0,
        "fat_per_100g": 16.8,
        "fiber_per_100g": 1.8,
        "serving_conversions": {"piece": 80.0, "bhatura": 80.0},
        "description": "Fluffy deep-fried leavened sourdough bread.",
    },
    # Dairy & Sweets / Desserts
    {
        "id": "curd_dahi",
        "name": "Plain Curd (Dahi)",
        "hindi_name": "सादा दही",
        "category": "Dairy",
        "calories_per_100g": 60.0,
        "protein_per_100g": 3.5,
        "carbs_per_100g": 4.5,
        "fat_per_100g": 3.2,
        "fiber_per_100g": 0.0,
        "serving_conversions": {"katori": 150.0, "cup": 200.0, "tbsp": 20.0},
        "description": "Traditional homemade Indian whole milk yogurt.",
    },
    {
        "id": "paneer_raw",
        "name": "Paneer (Fresh Cottage Cheese)",
        "hindi_name": "पनीर",
        "category": "Dairy",
        "calories_per_100g": 265.0,
        "protein_per_100g": 18.3,
        "carbs_per_100g": 3.4,
        "fat_per_100g": 20.8,
        "fiber_per_100g": 0.0,
        "serving_conversions": {"piece": 20.0, "serving": 60.0, "cup": 120.0},
        "description": "Unsalted whole milk fresh cheese.",
    },
    {
        "id": "gulab_jamun",
        "name": "Gulab Jamun",
        "hindi_name": "गुलाब जामुन",
        "category": "Sweets",
        "calories_per_100g": 340.0,
        "protein_per_100g": 4.8,
        "carbs_per_100g": 56.0,
        "fat_per_100g": 11.2,
        "fiber_per_100g": 0.5,
        "serving_conversions": {"piece": 45.0, "serving": 90.0},
        "description": "Deep-fried milk-solid dumplings soaked in scented sugar syrup.",
    },
    {
        "id": "rasgulla",
        "name": "Rasgulla",
        "hindi_name": "रसगुल्ला",
        "category": "Sweets",
        "calories_per_100g": 186.0,
        "protein_per_100g": 4.2,
        "carbs_per_100g": 38.5,
        "fat_per_100g": 1.8,
        "fiber_per_100g": 0.2,
        "serving_conversions": {"piece": 45.0, "serving": 90.0},
        "description": "Soft cottage cheese dumplings simmered in light sugar syrup.",
    },
    {
        "id": "masala_chai",
        "name": "Masala Chai (with milk & sugar)",
        "hindi_name": "मसाला चाय",
        "category": "Beverages",
        "calories_per_100g": 65.0,
        "protein_per_100g": 2.2,
        "carbs_per_100g": 9.5,
        "fat_per_100g": 2.0,
        "fiber_per_100g": 0.1,
        "serving_conversions": {"cup": 150.0, "cutting": 80.0, "mug": 250.0},
        "description": "Brewed black tea with spices, milk, and sugar.",
    },
    {
        "id": "sweet_lassi",
        "name": "Sweet Lassi",
        "hindi_name": "मीठी लस्सी",
        "category": "Beverages",
        "calories_per_100g": 110.0,
        "protein_per_100g": 3.1,
        "carbs_per_100g": 16.0,
        "fat_per_100g": 3.6,
        "fiber_per_100g": 0.0,
        "serving_conversions": {"glass": 250.0, "cup": 180.0},
        "description": "Churned yogurt beverage sweetened with sugar and cardamoms.",
    },
    {
        "id": "buttermilk_chaas",
        "name": "Chaas / Buttermilk (Spiced)",
        "hindi_name": "छाछ / मट्ठा",
        "category": "Beverages",
        "calories_per_100g": 25.0,
        "protein_per_100g": 1.5,
        "carbs_per_100g": 2.2,
        "fat_per_100g": 1.0,
        "fiber_per_100g": 0.2,
        "serving_conversions": {"glass": 250.0, "cup": 180.0},
        "description": "Diluted savory yogurt seasoned with roasted cumin, salt, and mint.",
    },
]


class NutritionCalculator:
    """
    Main calculator for searching Indian foods, estimating nutrition
    by custom serving/weight, calculating meals, and daily dietary metrics.
    """

    def __init__(self, data_file_path: Optional[str] = None):
        self.food_database: Dict[str, FoodItem] = {}
        self.load_database(data_file_path)

    def load_database(self, data_file_path: Optional[str] = None) -> None:
        """Loads food database from a JSON file or initializes with default dataset."""
        # Check if a custom file is provided
        target_path: Optional[Path] = None
        if data_file_path:
            target_path = Path(data_file_path)
        else:
            # Check default data path: ../data/indian_food_nutrition.json
            potential_data_path = (
                Path(__file__).resolve().parent.parent / "data" / "indian_food_nutrition.json"
            )
            if potential_data_path.exists():
                target_path = potential_data_path

        items_to_load = DEFAULT_INDIAN_FOODS

        if target_path and target_path.exists():
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    custom_items = json.load(f)
                    if isinstance(custom_items, list):
                        items_to_load = custom_items
            except Exception as err:
                print(f"Warning: Could not read {target_path} ({err}). Using default foods.")

        # Populate internal dict
        self.food_database.clear()
        for item in items_to_load:
            food = FoodItem(
                id=item["id"],
                name=item["name"],
                hindi_name=item.get("hindi_name"),
                category=item.get("category", "General"),
                calories_per_100g=float(item.get("calories_per_100g", 0.0)),
                protein_per_100g=float(item.get("protein_per_100g", 0.0)),
                carbs_per_100g=float(item.get("carbs_per_100g", 0.0)),
                fat_per_100g=float(item.get("fat_per_100g", 0.0)),
                fiber_per_100g=float(item.get("fiber_per_100g", 0.0)),
                serving_conversions=item.get("serving_conversions", {}),
                description=item.get("description", ""),
            )
            self.food_database[food.id.lower()] = food

    def export_database_json(self, output_path: str) -> None:
        """Exports the active database to a JSON file (useful for initializing data folder)."""
        data = []
        for food in self.food_database.values():
            data.append(
                {
                    "id": food.id,
                    "name": food.name,
                    "hindi_name": food.hindi_name,
                    "category": food.category,
                    "calories_per_100g": food.calories_per_100g,
                    "protein_per_100g": food.protein_per_100g,
                    "carbs_per_100g": food.carbs_per_100g,
                    "fat_per_100g": food.fat_per_100g,
                    "fiber_per_100g": food.fiber_per_100g,
                    "serving_conversions": food.serving_conversions,
                    "description": food.description,
                }
            )
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_all_foods(self) -> List[FoodItem]:
        """Returns a list of all food items in the database."""
        return list(self.food_database.values())

    def get_categories(self) -> List[str]:
        """Returns a sorted list of unique categories."""
        categories = {f.category for f in self.food_database.values()}
        return sorted(list(categories))

    def find_food(self, query: str) -> Optional[FoodItem]:
        """
        Exact or best match for a given query string (matches id, english name, or hindi name).
        """
        q = query.strip().lower()

        # Direct id match
        if q in self.food_database:
            return self.food_database[q]

        # Direct name match
        for food in self.food_database.values():
            if food.name.lower() == q or (food.hindi_name and food.hindi_name.lower() == q):
                return food

        # Substring search
        matches = [
            food
            for food in self.food_database.values()
            if q in food.name.lower() or (food.hindi_name and q in food.hindi_name.lower())
        ]
        if matches:
            return matches[0]

        # Fuzzy match
        all_names = {food.name: food for food in self.food_database.values()}
        close_matches = difflib.get_close_matches(query, list(all_names.keys()), n=1, cutoff=0.5)
        if close_matches:
            return all_names[close_matches[0]]

        return None

    def search_foods(
        self, query: str = "", category: Optional[str] = None, limit: int = 20
    ) -> List[FoodItem]:
        """
        Searches foods with optional category filter, substring, and fuzzy matching.
        """
        q = query.strip().lower()
        results: List[FoodItem] = []

        pool = list(self.food_database.values())
        if category and category.lower() != "all":
            pool = [f for f in pool if f.category.lower() == category.lower()]

        if not q:
            return pool[:limit]

        # High priority: exact starts-with match
        starts_with = [
            f
            for f in pool
            if f.name.lower().startswith(q)
            or (f.hindi_name and f.hindi_name.lower().startswith(q))
        ]
        # Medium priority: contains substring
        contains = [
            f
            for f in pool
            if f not in starts_with
            and (q in f.name.lower() or (f.hindi_name and q in f.hindi_name.lower()))
        ]

        combined = starts_with + contains

        # If not enough matches, try fuzzy matching
        if len(combined) < limit:
            name_to_food = {f.name: f for f in pool if f not in combined}
            close_names = difflib.get_close_matches(
                query, list(name_to_food.keys()), n=limit - len(combined), cutoff=0.4
            )
            for c_name in close_names:
                combined.append(name_to_food[c_name])

        return combined[:limit]

    def calculate_item_nutrition(
        self, food_name_or_id: str, quantity: float, unit: str = "g"
    ) -> NutritionalInfo:
        """Calculates nutrition for an individual food item and serving size."""
        food = self.find_food(food_name_or_id)
        if not food:
            raise ValueError(f"Food '{food_name_or_id}' was not found in the database.")

        return food.calculate_nutrition(quantity, unit)

    def calculate_meal(self, items: List[Dict[str, Any]]) -> MealSummary:
        """
        Calculates total calories and macronutrient breakdown for a list of items.

        Each item dictionary should have:
        - 'food': food name or id (str)
        - 'quantity': float
        - 'unit': str (optional, defaults to 'g')
        """
        total_cal = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        total_fiber = 0.0
        total_weight = 0.0
        results: List[MealItemResult] = []

        for item in items:
            food_query = str(item.get("food", item.get("name", "")))
            quantity = float(item.get("quantity", 1.0))
            unit = str(item.get("unit", "g"))

            food = self.find_food(food_query)
            if not food:
                raise ValueError(f"Food item '{food_query}' not found.")

            nutrition = food.calculate_nutrition(quantity, unit)

            total_cal += nutrition.calories
            total_protein += nutrition.protein
            total_carbs += nutrition.carbohydrates
            total_fat += nutrition.fat
            total_fiber += nutrition.fiber
            total_weight += nutrition.serving_weight_g

            results.append(
                MealItemResult(
                    food_id=food.id,
                    food_name=food.name,
                    category=food.category,
                    quantity=quantity,
                    unit=unit,
                    weight_g=round(nutrition.serving_weight_g, 1),
                    calories=round(nutrition.calories, 1),
                    protein=round(nutrition.protein, 1),
                    carbs=round(nutrition.carbohydrates, 1),
                    fat=round(nutrition.fat, 1),
                    fiber=round(nutrition.fiber, 1),
                )
            )

        # Calculate macro calorie contributions
        # Protein: 4 kcal/g, Carbs: 4 kcal/g, Fat: 9 kcal/g
        protein_cal = total_protein * 4.0
        carbs_cal = total_carbs * 4.0
        fat_cal = total_fat * 9.0
        macro_cal_sum = protein_cal + carbs_cal + fat_cal

        if macro_cal_sum > 0:
            macro_percentages = {
                "protein": round((protein_cal / macro_cal_sum) * 100.0, 1),
                "carbohydrates": round((carbs_cal / macro_cal_sum) * 100.0, 1),
                "fat": round((fat_cal / macro_cal_sum) * 100.0, 1),
            }
        else:
            macro_percentages = {"protein": 0.0, "carbohydrates": 0.0, "fat": 0.0}

        return MealSummary(
            total_calories=round(total_cal, 1),
            total_protein=round(total_protein, 1),
            total_carbs=round(total_carbs, 1),
            total_fat=round(total_fat, 1),
            total_fiber=round(total_fiber, 1),
            total_weight_g=round(total_weight, 1),
            macro_percentages=macro_percentages,
            items=results,
        )

    @staticmethod
    def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str = "male") -> float:
        """
        Calculates Basal Metabolic Rate (BMR) using the Mifflin-St Jeor Equation.
        """
        # BMR = (10 × weight in kg) + (6.25 × height in cm) - (5 × age in years) + s
        # where s is +5 for males and -161 for females.
        s = 5 if gender.lower() in ("male", "m") else -161
        bmr = (10.0 * weight_kg) + (6.25 * height_cm) - (5.0 * age) + s
        return round(max(bmr, 500.0), 1)

    @staticmethod
    def calculate_tdee(bmr: float, activity_level: str = "sedentary") -> float:
        """
        Calculates Total Daily Energy Expenditure (TDEE) based on activity multiplier.
        """
        multipliers = {
            "sedentary": 1.2,  # Little or no exercise
            "lightly_active": 1.375,  # Light exercise 1-3 days/week
            "moderately_active": 1.55,  # Moderate exercise 3-5 days/week
            "very_active": 1.725,  # Hard exercise 6-7 days/week
            "extra_active": 1.9,  # Very hard exercise & physical job
        }
        mult = multipliers.get(activity_level.lower(), 1.2)
        return round(bmr * mult, 1)


if __name__ == "__main__":
    calc = NutritionCalculator()
    print(f"Loaded {len(calc.food_database)} Indian food items.")

    # Demonstration of search
    search_res = calc.search_foods("paneer")
    print(f"\nSearch for 'paneer' found {len(search_res)} items:")
    for f in search_res:
        print(f" - {f.name} ({f.calories_per_100g} kcal/100g)")

    # Demonstration of meal calculation
    sample_thali = [
        {"food": "roti", "quantity": 3, "unit": "piece"},
        {"food": "paneer butter masala", "quantity": 1, "unit": "katori"},
        {"food": "steamed white rice", "quantity": 1, "unit": "katori"},
        {"food": "dal tadka", "quantity": 1, "unit": "katori"},
        {"food": "plain curd", "quantity": 1, "unit": "katori"},
    ]

    meal_summary = calc.calculate_meal(sample_thali)
    print("\n--- Sample Indian Thali Meal Summary ---")
    print(f"Total Calories: {meal_summary.total_calories} kcal")
    print(f"Protein: {meal_summary.total_protein} g")
    print(f"Carbs: {meal_summary.total_carbs} g")
    print(f"Fat: {meal_summary.total_fat} g")
    print(f"Fiber: {meal_summary.total_fiber} g")
    print(f"Macro Split: {meal_summary.macro_percentages}")
    print("Items breakdown:")
    for item in meal_summary.items:
        print(f" • {item.quantity} {item.unit} {item.food_name}: {item.calories} kcal ({item.weight_g}g)")
