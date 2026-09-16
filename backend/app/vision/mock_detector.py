"""
Mock Vision Detector — Phase 5 Upgrade

WHAT IT DOES:
    Generates realistic, structured multi-food candidate detections with:
    - Bounding boxes [ymin, xmin, ymax, xmax] (normalized 0.0 to 1.0)
    - Instance counts (e.g. 2 rotis, 3 idlis, 1 omelette)
    - Segmentation mask flags
    - Deterministic scenarios for Omelette, Multi-Food Thalis, South Indian Breakfast, Biryani, and Unknown/Low-Confidence

WHY WE NEED IT:
    Allows full end-to-end development, testing, and evaluation of:
    1. Multi-food plate detection (up to 7 items simultaneously)
    2. Interactive SVG bounding box rendering on frontend
    3. Anti-false-positive testing (preventing Omelette -> Dal)
    4. Instance counting accuracy (e.g. Roti x 2, Idli x 3)
    5. Refusal/Uncertainty states for poor-quality inputs
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.vision.base import DetectedFood, VisionModel, VisionResult


class MockVisionModel(VisionModel):
    """
    Mock vision model simulating multi-food bounding box detection and classification.
    """

    @property
    def model_name(self) -> str:
        return "DietAI24 Mock Multi-Region Vision v2.0"

    @property
    def mode(self) -> str:
        return "mock"

    def detect_foods(self, image_path: str) -> VisionResult:
        path = Path(image_path)
        if not path.exists():
            return VisionResult(
                foods=[],
                model_name=self.model_name,
                mode=self.mode,
                error=f"Image file not found: {image_path}",
            )

        filename_lower = path.stem.lower()

        # Scenario 1: Omelette / Egg detection (Specific test requirement)
        if any(w in filename_lower for w in ["omelette", "omelet", "egg", "anda"]):
            return self._scenario_omelette()

        # Scenario 2: South Indian Dosa / Breakfast
        if "dosa" in filename_lower:
            return self._scenario_dosa()

        # Scenario 3: Idli breakfast with instance counting (3 idlis)
        if "idli" in filename_lower:
            return self._scenario_idli_counting()

        # Scenario 4: Samosa snacks with instance counting (2 samosas)
        if "samosa" in filename_lower:
            return self._scenario_samosa_counting()

        # Scenario 5: Biryani feast
        if any(w in filename_lower for w in ["biryani", "pulao"]):
            return self._scenario_biryani()

        # Scenario 6: Multi-food Thali (6+ items: Rice, Dal, Paneer, Roti, Salad, Curd)
        if any(w in filename_lower for w in ["thali", "plate", "meal", "combo"]):
            return self._scenario_indian_thali()

        # Scenario 7: Steamed white rice
        if any(w in filename_lower for w in ["rice", "chawal"]):
            return self._scenario_rice()

        # Scenario 8: Unknown / Ambiguous test image
        if any(w in filename_lower for w in ["unknown", "blur", "noise", "nonfood"]):
            return self._scenario_unknown()

        # Visual feature inspection on image file pixels
        visual_result = self._analyze_pixels(path)
        if visual_result is not None:
            return visual_result

        # Hash-based deterministic fallback for arbitrary images
        return self._scenario_by_hash(path)

    def _scenario_omelette(self) -> VisionResult:
        """Single food omelette test scenario."""
        return VisionResult(
            foods=[
                DetectedFood(
                    id="food_instance_1",
                    name="Plain Omelette",
                    confidence=0.94,
                    count=1,
                    bounding_box={"ymin": 0.12, "xmin": 0.18, "ymax": 0.82, "xmax": 0.82},
                    mask_available=True,
                    mask_polygon=[
                        [0.20, 0.15], [0.80, 0.15], [0.82, 0.80], [0.18, 0.80]
                    ],
                    estimated_grams=120.0,
                    visual_portion_size="medium",
                    container_type="plate",
                    visual_cues="Golden folded egg pancake with crisp edges and fresh herb garnish",
                )
            ],
            model_name=self.model_name,
            mode=self.mode,
            candidate_regions_count=1,
            raw_response="[MOCK_OMELETTE] Identified 1 egg pancake region with 94% visual confidence.",
        )

    def _scenario_dosa(self) -> VisionResult:
        """South Indian Dosa + Sambar + Chutney meal."""
        return VisionResult(
            foods=[
                DetectedFood(
                    id="food_instance_1",
                    name="Masala Dosa",
                    confidence=0.93,
                    count=1,
                    bounding_box={"ymin": 0.15, "xmin": 0.10, "ymax": 0.58, "xmax": 0.90},
                    mask_available=True,
                    estimated_grams=180.0,
                    visual_portion_size="medium",
                    container_type="plate",
                    visual_cues="Elongated crispy golden crepe rolled with spiced potato filling",
                ),
                DetectedFood(
                    id="food_instance_2",
                    name="Sambar",
                    confidence=0.88,
                    count=1,
                    bounding_box={"ymin": 0.62, "xmin": 0.10, "ymax": 0.92, "xmax": 0.48},
                    mask_available=True,
                    estimated_grams=150.0,
                    visual_portion_size="medium",
                    container_type="katori",
                    visual_cues="Tempered lentil soup with drumstick and mustard seeds",
                ),
                DetectedFood(
                    id="food_instance_3",
                    name="Coconut Chutney",
                    confidence=0.85,
                    count=1,
                    bounding_box={"ymin": 0.62, "xmin": 0.52, "ymax": 0.92, "xmax": 0.90},
                    mask_available=True,
                    estimated_grams=60.0,
                    visual_portion_size="small",
                    container_type="katori",
                    visual_cues="Ground coconut relish with tempered curry leaves",
                ),
            ],
            model_name=self.model_name,
            mode=self.mode,
            candidate_regions_count=3,
            raw_response="[MOCK_DOSA] 3 distinct food regions localized: Dosa, Sambar, Coconut Chutney.",
        )

    def _scenario_idli_counting(self) -> VisionResult:
        """Repeated food instance counting: 3 Idlis + Sambar + Chutney."""
        return VisionResult(
            foods=[
                DetectedFood(
                    id="food_instance_1",
                    name="Idli",
                    confidence=0.95,
                    count=3,
                    bounding_box={"ymin": 0.15, "xmin": 0.15, "ymax": 0.58, "xmax": 0.85},
                    mask_available=True,
                    estimated_grams=180.0,  # 3 * 60g
                    visual_portion_size="medium",
                    container_type="plate",
                    visual_cues="3 distinct steamed white fermented rice cakes with porous surface",
                ),
                DetectedFood(
                    id="food_instance_2",
                    name="Sambar",
                    confidence=0.89,
                    count=1,
                    bounding_box={"ymin": 0.62, "xmin": 0.12, "ymax": 0.92, "xmax": 0.50},
                    estimated_grams=150.0,
                    visual_portion_size="medium",
                    container_type="katori",
                    visual_cues="Spiced lentil accompaniment",
                ),
                DetectedFood(
                    id="food_instance_3",
                    name="Coconut Chutney",
                    confidence=0.86,
                    count=1,
                    bounding_box={"ymin": 0.62, "xmin": 0.55, "ymax": 0.92, "xmax": 0.88},
                    estimated_grams=60.0,
                    visual_portion_size="small",
                    container_type="katori",
                    visual_cues="White coconut relish",
                ),
            ],
            model_name=self.model_name,
            mode=self.mode,
            candidate_regions_count=3,
            raw_response="[MOCK_IDLI_COUNTING] Localized 3 individual idli cakes and 2 condiment bowls.",
        )

    def _scenario_samosa_counting(self) -> VisionResult:
        """Repeated food instance: 2 Samosas + Masala Chai."""
        return VisionResult(
            foods=[
                DetectedFood(
                    id="food_instance_1",
                    name="Samosa",
                    confidence=0.94,
                    count=2,
                    bounding_box={"ymin": 0.20, "xmin": 0.15, "ymax": 0.80, "xmax": 0.65},
                    mask_available=True,
                    estimated_grams=160.0,  # 2 * 80g
                    visual_portion_size="medium",
                    container_type="plate",
                    visual_cues="2 golden triangular deep-fried pastry cones with potato filling",
                ),
                DetectedFood(
                    id="food_instance_2",
                    name="Masala Chai",
                    confidence=0.87,
                    count=1,
                    bounding_box={"ymin": 0.25, "xmin": 0.70, "ymax": 0.75, "xmax": 0.92},
                    estimated_grams=150.0,
                    visual_portion_size="medium",
                    container_type="cup",
                    visual_cues="Brewed milk tea in glass tumbler",
                ),
            ],
            model_name=self.model_name,
            mode=self.mode,
            candidate_regions_count=2,
            raw_response="[MOCK_SAMOSA] Counted 2 distinct samosas + 1 cup of chai.",
        )

    def _scenario_biryani(self) -> VisionResult:
        """Biryani Feast: Biryani, Raita, Salad."""
        return VisionResult(
            foods=[
                DetectedFood(
                    id="food_instance_1",
                    name="Chicken Biryani",
                    confidence=0.95,
                    count=1,
                    bounding_box={"ymin": 0.15, "xmin": 0.12, "ymax": 0.70, "xmax": 0.88},
                    mask_available=True,
                    estimated_grams=350.0,
                    visual_portion_size="large",
                    container_type="plate",
                    visual_cues="Long-grain basmati layered with saffron rice and tender spiced meat",
                ),
                DetectedFood(
                    id="food_instance_2",
                    name="Raita",
                    confidence=0.88,
                    count=1,
                    bounding_box={"ymin": 0.72, "xmin": 0.12, "ymax": 0.95, "xmax": 0.48},
                    estimated_grams=100.0,
                    visual_portion_size="medium",
                    container_type="katori",
                    visual_cues="Whisked spiced curd with cucumber and cumin",
                ),
                DetectedFood(
                    id="food_instance_3",
                    name="Cucumber Tomato Salad",
                    confidence=0.84,
                    count=1,
                    bounding_box={"ymin": 0.72, "xmin": 0.52, "ymax": 0.95, "xmax": 0.88},
                    estimated_grams=80.0,
                    visual_portion_size="small",
                    container_type="katori",
                    visual_cues="Fresh sliced salad greens and onion rings",
                ),
            ],
            model_name=self.model_name,
            mode=self.mode,
            candidate_regions_count=3,
            raw_response="[MOCK_BIRYANI] Detected Biryani platter with 2 side accompaniments.",
        )

    def _scenario_indian_thali(self) -> VisionResult:
        """
        Comprehensive Multi-Food Plate (6 items):
        Rice, Dal Tadka, Paneer Butter Masala, Roti (count: 2), Salad, Curd
        """
        return VisionResult(
            foods=[
                DetectedFood(
                    id="food_instance_1",
                    name="Steamed White Rice",
                    confidence=0.95,
                    count=1,
                    bounding_box={"ymin": 0.32, "xmin": 0.35, "ymax": 0.68, "xmax": 0.65},
                    mask_available=True,
                    estimated_grams=180.0,
                    visual_portion_size="medium",
                    container_type="center_plate",
                    visual_cues="Central mound of steamed white rice grains",
                ),
                DetectedFood(
                    id="food_instance_2",
                    name="Yellow Dal Tadka",
                    confidence=0.91,
                    count=1,
                    bounding_box={"ymin": 0.08, "xmin": 0.55, "ymax": 0.35, "xmax": 0.85},
                    mask_available=True,
                    estimated_grams=150.0,
                    visual_portion_size="medium",
                    container_type="katori",
                    visual_cues="Turmeric-yellow tempered lentil broth with ghee tadka",
                ),
                DetectedFood(
                    id="food_instance_3",
                    name="Paneer Butter Masala",
                    confidence=0.92,
                    count=1,
                    bounding_box={"ymin": 0.08, "xmin": 0.15, "ymax": 0.35, "xmax": 0.45},
                    mask_available=True,
                    estimated_grams=160.0,
                    visual_portion_size="medium",
                    container_type="katori",
                    visual_cues="Rich tomato-cream gravy with cottage cheese cubes",
                ),
                DetectedFood(
                    id="food_instance_4",
                    name="Roti",
                    confidence=0.93,
                    count=2,
                    bounding_box={"ymin": 0.65, "xmin": 0.12, "ymax": 0.95, "xmax": 0.45},
                    mask_available=True,
                    estimated_grams=70.0,  # 2 * 35g
                    visual_portion_size="medium",
                    container_type="plate",
                    visual_cues="Stack of 2 puffed whole-wheat rotis with charred spots",
                ),
                DetectedFood(
                    id="food_instance_5",
                    name="Cucumber Tomato Salad",
                    confidence=0.86,
                    count=1,
                    bounding_box={"ymin": 0.65, "xmin": 0.55, "ymax": 0.95, "xmax": 0.88},
                    mask_available=True,
                    estimated_grams=80.0,
                    visual_portion_size="small",
                    container_type="katori",
                    visual_cues="Fresh sliced cucumbers, carrots, and onions",
                ),
                DetectedFood(
                    id="food_instance_6",
                    name="Curd",
                    confidence=0.89,
                    count=1,
                    bounding_box={"ymin": 0.38, "xmin": 0.72, "ymax": 0.65, "xmax": 0.95},
                    mask_available=True,
                    estimated_grams=100.0,
                    visual_portion_size="small",
                    container_type="katori",
                    visual_cues="Plain creamy set yogurt",
                ),
            ],
            model_name=self.model_name,
            mode=self.mode,
            candidate_regions_count=6,
            raw_response="[MOCK_THALI] Segmented 6 distinct food regions across the thali plate.",
        )

    def _scenario_rice(self) -> VisionResult:
        return VisionResult(
            foods=[
                DetectedFood(
                    id="food_instance_1",
                    name="Steamed White Rice",
                    confidence=0.96,
                    count=1,
                    bounding_box={"ymin": 0.15, "xmin": 0.15, "ymax": 0.85, "xmax": 0.85},
                    estimated_grams=200.0,
                    visual_portion_size="medium",
                    container_type="bowl",
                    visual_cues="Bowl filled with fluffy steamed white rice",
                )
            ],
            model_name=self.model_name,
            mode=self.mode,
            candidate_regions_count=1,
            raw_response="[MOCK_RICE] 1 rice bowl region localized.",
        )

    def _scenario_unknown(self) -> VisionResult:
        """Low-confidence / ambiguous image test case."""
        return VisionResult(
            foods=[
                DetectedFood(
                    id="food_instance_1",
                    name="Unknown Food / Ambiguous Item",
                    confidence=0.28,
                    count=1,
                    count_uncertain=True,
                    bounding_box={"ymin": 0.30, "xmin": 0.30, "ymax": 0.70, "xmax": 0.70},
                    visual_portion_size="medium",
                    visual_cues="Low resolution or obscured subject; lacks distinguishing culinary characteristics",
                )
            ],
            model_name=self.model_name,
            mode=self.mode,
            candidate_regions_count=1,
            raw_response="[MOCK_UNKNOWN] Low confidence detection (0.28). Recommend user verification.",
        )

    def _analyze_pixels(self, path: Path) -> Optional[VisionResult]:
        """
        Pixel-level analysis for images uploaded without food names.
        Differentiates between Omelette (flat pancake with herbs) vs Dal vs Rice.
        """
        try:
            from PIL import Image, ImageStat
            with Image.open(path) as img:
                img = img.convert("RGB")
                w, h = img.size

                # Sample statistics
                thumb = img.resize((100, 100))
                stat = ImageStat.Stat(thumb)
                r_mean, g_mean, b_mean = stat.mean[:3]
                brightness = (r_mean * 299 + g_mean * 587 + b_mean * 114) / 1000.0

                # 1. White grains / Steamed Rice
                max_diff = max(abs(r_mean - g_mean), abs(g_mean - b_mean), abs(r_mean - b_mean))
                if brightness > 160 and max_diff < 30:
                    return self._scenario_rice()

                # 2. Golden-yellow with herbal green flecks or pan-fried surface (like the user's Omelette!)
                # In the user's omelette image, yellow egg body with green herbs and grey/blue background
                if r_mean > 115 and g_mean > 95 and b_mean < 90:
                    # Examine center crop to check if it's a flat circular/folded egg surface
                    center_crop = img.crop((int(w * 0.2), int(h * 0.2), int(w * 0.8), int(h * 0.8)))
                    center_stat = ImageStat.Stat(center_crop.resize((50, 50)))
                    cr, cg, cb = center_stat.mean[:3]

                    # If yellow/golden egg surface: classify as Plain Omelette or Masala Omelette
                    if cr > 120 and cg > 100:
                        return VisionResult(
                            foods=[
                                DetectedFood(
                                    id="food_instance_1",
                                    name="Plain Omelette",
                                    confidence=0.93,
                                    count=1,
                                    bounding_box={"ymin": 0.15, "xmin": 0.20, "ymax": 0.85, "xmax": 0.80},
                                    mask_available=True,
                                    mask_polygon=[
                                        [0.22, 0.18], [0.78, 0.18], [0.80, 0.82], [0.20, 0.82]
                                    ],
                                    estimated_grams=120.0,
                                    visual_portion_size="medium",
                                    container_type="plate",
                                    visual_cues="Golden-yellow pan-fried egg omelette with seasoned herbs",
                                )
                            ],
                            model_name=self.model_name,
                            mode=self.mode,
                            candidate_regions_count=1,
                            raw_response="[PIXEL_VISION] Recognized pan-fried omelette surface with herb flecks.",
                        )
        except Exception:
            pass
        return None

    def _scenario_by_hash(self, path: Path) -> VisionResult:
        """Deterministic scenario rotation based on file hash."""
        scenarios = [
            self._scenario_omelette,
            self._scenario_indian_thali,
            self._scenario_dosa,
            self._scenario_biryani,
            self._scenario_idli_counting,
            self._scenario_samosa_counting,
        ]
        try:
            h = int(hashlib.md5(path.read_bytes()).hexdigest(), 16)
            idx = h % len(scenarios)
        except Exception:
            idx = 0
        return scenarios[idx]()
