"""
Portion Estimation — Phase 6

WHAT IT DOES:
    Estimates the portion size (in grams) for a detected food item.

WHY WE NEED IT:
    The nutrition database stores values per 100g.
    To calculate actual calories, we need to know HOW MUCH food is on the plate.
    Since we can't measure grams from a normal photo, we use category-based
    default portions (small/medium/large).

HOW IT WORKS:
    detected food name + category → default portion for that category
    → { size_label: "medium", estimated_grams: 150, method: "MVP_RULE_BASED" }

IMPORTANT LIMITATION:
    This is an APPROXIMATE estimation using rule-based defaults.
    It does NOT measure actual food weight from the image.
    Future versions could use depth cameras or reference objects for accuracy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class PortionEstimate:
    """
    Estimated portion size for a food item.

    All estimates are clearly labeled with the estimation method
    so users know these are approximations, not measurements.
    """
    size_label: str          # "small", "medium", "large"
    estimated_grams: float   # Weight estimate in grams
    method: str              # Always "MVP_RULE_BASED" for now
    confidence: float        # How confident we are (low for rule-based)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "size_label": self.size_label,
            "estimated_grams": self.estimated_grams,
            "method": self.method,
            "confidence": round(self.confidence, 2),
        }


# ---------------------------------------------------------------------------
# Category-based portion defaults (grams)
# These are configurable approximations, NOT exact measurements.
# ---------------------------------------------------------------------------

# Format: { category: { "small": grams, "medium": grams, "large": grams } }
CATEGORY_PORTIONS: Dict[str, Dict[str, float]] = {
    "Rice Dishes": {"small": 120, "medium": 200, "large": 350},
    "Breads": {"small": 30, "medium": 60, "large": 100},
    "Dals and Lentils": {"small": 100, "medium": 150, "large": 220},
    "Curries": {"small": 100, "medium": 150, "large": 220},
    "South Indian": {"small": 60, "medium": 120, "large": 200},
    "Breakfast": {"small": 100, "medium": 150, "large": 220},
    "Snacks": {"small": 40, "medium": 80, "large": 120},
    "Dairy": {"small": 50, "medium": 100, "large": 200},
    "Beverages": {"small": 100, "medium": 150, "large": 250},
    "Sweets": {"small": 30, "medium": 50, "large": 100},
    "Vegetables": {"small": 50, "medium": 80, "large": 130},
    "Condiments": {"small": 5, "medium": 10, "large": 20},
}

# Default if category is unknown
DEFAULT_PORTIONS = {"small": 80, "medium": 150, "large": 250}


# ---------------------------------------------------------------------------
# Category-based density map (g/cm³) and container references
# Research basis: Nutrition5k and DietAI24 volumetric density modeling.
# ---------------------------------------------------------------------------

CATEGORY_DENSITIES: Dict[str, float] = {
    "Rice Dishes": 0.82,       # Cooked grains ~ 0.80 - 0.85 g/cm³
    "Breads": 0.45,            # Leavened & unleavened flatbreads
    "Dals and Lentils": 1.04,  # Thick simmered legume stews
    "Curries": 1.05,           # Spiced gravies with gravy/solid matrix
    "South Indian": 0.70,      # Fermented steamed or fried batter
    "Breakfast": 0.75,         # Poha, upma, khichdi
    "Snacks": 0.60,            # Hollow or puffed fritters/chaat
    "Dairy": 1.02,             # Yogurt / Curd
    "Beverages": 1.03,         # Chai, lassi, coffee
    "Sweets": 1.25,            # Dense sugar syrup / khoya / ghee
    "Vegetables": 0.65,        # Dry sauteed sabzi
    "Condiments": 1.10,        # Thick chutneys and pickles
}

CONTAINER_VOLUMES_CM3: Dict[str, float] = {
    "katori": 150.0,           # Standard Indian stainless steel katori (~150 ml)
    "small_bowl": 150.0,
    "serving_bowl": 300.0,
    "plate_portion": 220.0,    # Approx 1/3 of a 25cm dinner plate
    "cup": 180.0,
    "glass": 250.0,
}


def estimate_portion(
    food_name: str,
    category: str,
    default_portion_g: Optional[float] = None,
    size_hint: str = "medium",
    visual_grams_hint: Optional[float] = None,
    container_type: Optional[str] = None,
) -> PortionEstimate:
    """
    Estimate the portion size for a food item using multi-tier heuristics:
    
    Strategy:
    1. If visual_grams_hint was provided by a vision model / visual feature analyzer,
       validate and use it (method="VISUAL_VLM_ESTIMATE").
    2. If a container reference is provided, compute weight = Volume (cm³) * Density (g/cm³)
       (method="EMPIRICAL_DENSITY_ESTIMATE").
    3. Otherwise, use database default calibrated with size_hint (small/medium/large).
    4. Fall back to culinary category standard portions.
    """
    size_hint = (size_hint or "medium").lower().strip()
    if size_hint not in ("small", "medium", "large"):
        size_hint = "medium"

    # Strategy 1: Visual Mass Hint from Vision Perception
    if visual_grams_hint and visual_grams_hint > 0:
        # Sanity bound: keep within reasonable culinary limits (5g to 1500g)
        bounded_grams = max(5.0, min(1500.0, float(visual_grams_hint)))
        return PortionEstimate(
            size_label=size_hint,
            estimated_grams=round(bounded_grams, 1),
            method="VISUAL_VLM_ESTIMATE",
            confidence=0.78,
        )

    # Strategy 2: Empirical Container Volume * Category Density
    if container_type and container_type.lower() in CONTAINER_VOLUMES_CM3:
        vol = CONTAINER_VOLUMES_CM3[container_type.lower()]
        density = CATEGORY_DENSITIES.get(category, 0.90)
        calc_grams = vol * density
        if size_hint == "small":
            calc_grams *= 0.7
        elif size_hint == "large":
            calc_grams *= 1.4
        return PortionEstimate(
            size_label=size_hint,
            estimated_grams=round(calc_grams, 1),
            method="EMPIRICAL_DENSITY_ESTIMATE",
            confidence=0.65,
        )

    # Strategy 3: Database default with size scaling
    if default_portion_g and default_portion_g > 0:
        if size_hint == "small":
            grams = default_portion_g * 0.6
        elif size_hint == "large":
            grams = default_portion_g * 1.5
        else:
            grams = default_portion_g

        return PortionEstimate(
            size_label=size_hint,
            estimated_grams=round(grams, 0),
            method="MVP_RULE_BASED",
            confidence=0.5,
        )

    # Strategy 4: Use category-based defaults
    portions = CATEGORY_PORTIONS.get(category, DEFAULT_PORTIONS)
    grams = portions.get(size_hint, portions.get("medium", 150))

    return PortionEstimate(
        size_label=size_hint,
        estimated_grams=round(grams, 0),
        method="MVP_RULE_BASED",
        confidence=0.4,
    )


def apply_portion_override(
    estimate: PortionEstimate,
    override_grams: float,
) -> PortionEstimate:
    """
    Override the estimated portion with a user-provided value.

    This is important because users should be able to correct
    the system's estimates for more accurate results.

    Args:
        estimate: Original portion estimate.
        override_grams: User-provided weight in grams.

    Returns:
        New PortionEstimate with the overridden value.
    """
    return PortionEstimate(
        size_label="custom",
        estimated_grams=round(override_grams, 0),
        method="USER_OVERRIDE",
        confidence=0.9,  # User-provided values are more reliable
    )
