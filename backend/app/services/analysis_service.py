"""
Analysis Service — Phase 7

WHAT IT DOES:
    Orchestrates the ENTIRE pipeline from image to nutrition results.
    This is the "brain" that connects all the modules together.

WHY WE NEED IT:
    The API route handler should be simple — it just calls this service.
    All the complex pipeline logic lives here.

HOW DATA FLOWS:
    1. Receive image
    2. Vision model → detected foods
    3. For each food:
       a. Normalize name
       b. RAG retrieval → standardized food record
       c. Estimate portion
       d. Calculate nutrition
    4. Aggregate meal totals
    5. Return structured response
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path for direct execution (e.g. VS Code "Run" button)
_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend.app.config import settings
from backend.app.nutrition.calculator import (
    PortionNutrition,
    calculate_meal,
    calculate_nutrition,
)
from backend.app.nutrition.database import FoodDatabase, FoodRecord
from backend.app.nutrition.portion import (
    PortionEstimate,
    estimate_portion,
    apply_portion_override,
)
from backend.app.rag.matcher import MatchStatus, StrictFoodMatcher
from backend.app.rag.pipeline import RAGPipeline
from backend.app.rag.retriever import RetrievalResult
from backend.app.schemas.analysis import (
    AnalyzedFoodItem,
    AnalysisDebugInfo,
    AnalysisResponse,
    MealTotals,
    NutritionSchema,
    PortionSchema,
)
from backend.app.utils.logger import logger
from backend.app.vision.base import VisionModel, VisionResult


class AnalysisService:
    """
    Complete meal analysis pipeline.

    Connects:
    - Vision model (mock or Claude)
    - Food database + normalization
    - RAG retrieval
    - Portion estimation
    - Nutrition calculation

    WHAT I SHOULD SEE WHEN IT WORKS:
        >>> service = AnalysisService(vision_model, rag_pipeline)
        >>> result = service.analyze_image("path/to/meal.jpg")
        >>> print(result.status)
        success
        >>> print(result.foods[0].standardized_name)
        Chicken Biryani
    """

    def __init__(
        self,
        vision_model: VisionModel,
        rag_pipeline: RAGPipeline,
    ):
        self.vision_model = vision_model
        self.rag_pipeline = rag_pipeline

    def analyze_image(
        self,
        image_path: str,
        portion_overrides: Optional[Dict[str, float]] = None,
        debug: bool = False,
    ) -> AnalysisResponse:
        """
        Analyze a meal image and return nutrition estimates.

        Args:
            image_path: Path to the uploaded image file.
            portion_overrides: Optional dict of {food_id: grams} to override portions.
            debug: Whether to include debug information in the response.

        Returns:
            AnalysisResponse with detected foods, nutrition, and totals.
        """
        analysis_id = uuid.uuid4().hex[:12]
        logger.info(f"[{analysis_id}] Starting meal analysis")

        # ---------------------------------------------------
        # Step 1: Vision — detect foods in the image
        # ---------------------------------------------------
        logger.info(f"[{analysis_id}] Running vision model ({self.vision_model.mode})")
        vision_result: VisionResult = self.vision_model.detect_foods(image_path)

        if not vision_result.success:
            logger.warning(f"[{analysis_id}] Vision failed: {vision_result.error}")
            return AnalysisResponse(
                status="error",
                analysis_id=analysis_id,
                vision_mode=self.vision_model.mode,
                error=vision_result.error or "No food items could be identified in the image.",
            )

        logger.info(
            f"[{analysis_id}] Detected {len(vision_result.foods)} foods: "
            f"{[f.name for f in vision_result.foods]}"
        )

        # ---------------------------------------------------
        # Step 2-5: Process each detected food
        # ---------------------------------------------------
        from PIL import Image
        img_dimensions = {"width": 800, "height": 600}
        try:
            with Image.open(image_path) as im:
                img_dimensions = {"width": im.width, "height": im.height}
        except Exception:
            pass

        # ---------------------------------------------------
        # Step 2-5: Process each detected food instance
        # ---------------------------------------------------
        matcher = StrictFoodMatcher(
            retriever=self.rag_pipeline.retriever,
            database=self.rag_pipeline.database,
        )

        analyzed_foods: List[AnalyzedFoodItem] = []
        portion_nutritions: List[PortionNutrition] = []
        debug_retrievals: List[Dict[str, Any]] = []
        warnings: List[str] = []

        for idx, detected in enumerate(vision_result.foods, start=1):
            instance_id = detected.id or f"food_instance_{idx}"
            logger.info(f"[{analysis_id}] Processing instance {instance_id}: '{detected.name}' (count: {detected.count})")

            # Step 2: Strict Normalization + Anti-False-Positive Matching
            match_res = matcher.match(
                query=detected.name,
                visual_confidence=detected.confidence,
                top_k=5,
            )

            # Debug tracking
            debug_retrievals.append({
                "instance_id": instance_id,
                "query": detected.name,
                "visual_confidence": detected.confidence,
                "status": match_res.status.value,
                "top_candidates": match_res.top_candidates,
                "rejected_candidates": match_res.rejected_candidates,
            })

            # Handle Rejection / Uncertainty States
            if not match_res.is_accepted or match_res.food_record is None:
                warnings.append(match_res.explanation)
                analyzed_foods.append(AnalyzedFoodItem(
                    instance_id=instance_id,
                    detected_name=detected.name,
                    standardized_name=f"{detected.name.title()} (Review Needed)",
                    food_id="UNAVAILABLE",
                    category="Uncertain / Unindexed",
                    count=detected.count,
                    count_uncertain=detected.count_uncertain,
                    recognition_confidence=float(detected.confidence),
                    retrieval_confidence="low" if match_res.status == MatchStatus.LOW_CONFIDENCE else "unavailable",
                    retrieval_score=round(float(match_res.confidence_score), 3),
                    match_status=match_res.status.value,
                    needs_user_review=True,
                    detection={
                        "bbox": detected.bounding_box,
                        "mask_available": detected.mask_available,
                        "mask_polygon": detected.mask_polygon,
                    },
                    nutrition_match={
                        "food_id": None,
                        "name": detected.name,
                        "retrieval_score": round(float(match_res.confidence_score), 3),
                        "status": match_res.status.value,
                        "explanation": match_res.explanation,
                    },
                    portion=PortionSchema(
                        size_label="uncertain",
                        estimated_grams=0.0,
                        method="UNCERTAIN_INPUT",
                        confidence=0.0,
                    ),
                    nutrition=NutritionSchema(
                        calories_kcal=0.0,
                        protein_g=0.0,
                        carbs_g=0.0,
                        fat_g=0.0,
                        fiber_g=0.0,
                    ),
                    source="SYSTEM_REFUSAL",
                ))
                continue

            food_record: FoodRecord = match_res.food_record
            retrieval_conf = "high" if match_res.status in (MatchStatus.EXACT_MATCH, MatchStatus.HIGH_CONFIDENCE) else "medium"
            if match_res.status == MatchStatus.MEDIUM_CONFIDENCE:
                warnings.append(match_res.explanation)

            # Step 3: Portion estimation (accounting for count e.g. 2 rotis, 3 idlis)
            override = None
            if portion_overrides and food_record.food_id in portion_overrides:
                override = portion_overrides[food_record.food_id]

            # Base single-item default or detected mass
            single_default = food_record.default_portion_g
            total_default = single_default * max(1, detected.count)

            if override:
                portion_est = apply_portion_override(
                    estimate_portion(
                        food_name=food_record.food_name,
                        category=food_record.category,
                        default_portion_g=total_default,
                        size_hint=detected.visual_portion_size or "medium",
                        visual_grams_hint=detected.estimated_grams,
                        container_type=detected.container_type,
                    ),
                    override,
                )
            else:
                portion_est = estimate_portion(
                    food_name=food_record.food_name,
                    category=food_record.category,
                    default_portion_g=total_default,
                    size_hint=detected.visual_portion_size or "medium",
                    visual_grams_hint=detected.estimated_grams,
                    container_type=detected.container_type,
                )

            logger.info(
                f"[{analysis_id}] Portion for '{food_record.food_name}' (count: {detected.count}): "
                f"{portion_est.estimated_grams}g ({portion_est.method})"
            )

            # Step 4: Deterministic nutrition calculation
            nutrition_per_100g = food_record.to_nutrition_per_100g()
            calculated = calculate_nutrition(
                food_name=food_record.food_name,
                nutrition_per_100g=nutrition_per_100g,
                portion_grams=portion_est.estimated_grams,
            )
            portion_nutritions.append(calculated)

            # Build response item
            analyzed_foods.append(AnalyzedFoodItem(
                instance_id=instance_id,
                detected_name=detected.name,
                standardized_name=food_record.food_name,
                food_id=food_record.food_id,
                category=food_record.category,
                count=detected.count,
                count_uncertain=detected.count_uncertain,
                recognition_confidence=float(detected.confidence),
                retrieval_confidence=retrieval_conf,
                retrieval_score=round(float(match_res.confidence_score), 3),
                match_status=match_res.status.value,
                needs_user_review=match_res.needs_user_review,
                detection={
                    "bbox": detected.bounding_box,
                    "mask_available": detected.mask_available,
                    "mask_polygon": detected.mask_polygon,
                },
                nutrition_match={
                    "food_id": food_record.food_id,
                    "name": food_record.food_name,
                    "retrieval_score": round(float(match_res.confidence_score), 3),
                    "status": match_res.status.value,
                    "explanation": match_res.explanation,
                },
                portion=PortionSchema(
                    size_label=portion_est.size_label,
                    estimated_grams=float(portion_est.estimated_grams),
                    method=portion_est.method,
                    confidence=float(portion_est.confidence),
                ),
                nutrition=NutritionSchema(
                    calories_kcal=float(calculated.calories_kcal),
                    protein_g=float(calculated.protein_g),
                    carbs_g=float(calculated.carbs_g),
                    fat_g=float(calculated.fat_g),
                    fiber_g=float(calculated.fiber_g) if calculated.fiber_g is not None else None,
                ),
                source=food_record.source,
            ))

        # ---------------------------------------------------
        # Step 5: Aggregate meal totals
        # ---------------------------------------------------
        if not analyzed_foods:
            return AnalysisResponse(
                status="error",
                analysis_id=analysis_id,
                vision_mode=self.vision_model.mode,
                error=(
                    "Food items were detected but could not be matched "
                    "to any records in the nutrition database."
                ),
            )

        meal = calculate_meal(portion_nutritions)

        totals = MealTotals(
            calories_kcal=meal.total_calories_kcal,
            protein_g=meal.total_protein_g,
            carbs_g=meal.total_carbs_g,
            fat_g=meal.total_fat_g,
            fiber_g=meal.total_fiber_g,
            total_weight_g=meal.total_weight_g,
            macro_split=meal.macro_split,
        )

        logger.info(
            f"[{analysis_id}] Analysis complete: "
            f"{len(analyzed_foods)} foods, "
            f"{totals.calories_kcal} total kcal"
        )

        # Build debug info
        debug_info = None
        if debug or settings.DEBUG_ANALYSIS:
            debug_info = AnalysisDebugInfo(
                vision_mode=self.vision_model.mode,
                vision_model=self.vision_model.model_name,
                vision_raw_response=vision_result.raw_response,
                retrieval_details=debug_retrievals,
                candidate_regions_count=vision_result.candidate_regions_count or len(vision_result.foods),
            )

        return AnalysisResponse(
            status="success",
            analysis_id=analysis_id,
            image=img_dimensions,
            foods=analyzed_foods,
            totals=totals,
            food_count=len(analyzed_foods),
            vision_mode=self.vision_model.mode,
            warnings=warnings,
            debug=debug_info,
        )

    def recalculate(
        self,
        corrections: List[Dict[str, Any]],
    ) -> AnalysisResponse:
        """
        Recalculate nutrition based on user corrections.

        Args:
            corrections: List of {"food_id": "IF002", "portion_grams": 300}

        Returns:
            New AnalysisResponse with recalculated values.
        """
        analysis_id = uuid.uuid4().hex[:12]
        analyzed_foods: List[AnalyzedFoodItem] = []
        portion_nutritions: List[PortionNutrition] = []

        db = self.rag_pipeline.database
        if db is None:
            return AnalysisResponse(
                status="error",
                analysis_id=analysis_id,
                vision_mode="recalculation",
                error="Food database not available for recalculation.",
            )

        for item in corrections:
            food_id = item.get("food_id", "")
            portion_grams = float(item.get("grams") or item.get("portion_grams") or 150.0)

            food_record = db.get_by_id(food_id)
            if not food_record:
                continue

            nutrition_per_100g = food_record.to_nutrition_per_100g()
            calculated = calculate_nutrition(
                food_name=food_record.food_name,
                nutrition_per_100g=nutrition_per_100g,
                portion_grams=portion_grams,
            )
            portion_nutritions.append(calculated)

            analyzed_foods.append(AnalyzedFoodItem(
                detected_name=food_record.food_name.lower(),
                standardized_name=food_record.food_name,
                food_id=food_record.food_id,
                category=food_record.category,
                recognition_confidence=1.0,
                retrieval_confidence="high",
                retrieval_score=1.0,
                portion=PortionSchema(
                    size_label="custom",
                    estimated_grams=portion_grams,
                    method="USER_OVERRIDE",
                    confidence=0.9,
                ),
                nutrition=NutritionSchema(
                    calories_kcal=calculated.calories_kcal,
                    protein_g=calculated.protein_g,
                    carbs_g=calculated.carbs_g,
                    fat_g=calculated.fat_g,
                    fiber_g=calculated.fiber_g,
                ),
                source=food_record.source,
            ))

        meal = calculate_meal(portion_nutritions)

        totals = MealTotals(
            calories_kcal=meal.total_calories_kcal,
            protein_g=meal.total_protein_g,
            carbs_g=meal.total_carbs_g,
            fat_g=meal.total_fat_g,
            fiber_g=meal.total_fiber_g,
            total_weight_g=meal.total_weight_g,
            macro_split=meal.macro_split,
        ) if analyzed_foods else None

        return AnalysisResponse(
            status="success" if analyzed_foods else "error",
            analysis_id=analysis_id,
            foods=analyzed_foods,
            totals=totals,
            food_count=len(analyzed_foods),
            vision_mode="recalculation",
            error=None if analyzed_foods else "No valid foods found for recalculation.",
        )

    def _generate_fallback_record(self, name: str) -> FoodRecord:
        """
        Generate a calibrated fallback FoodRecord with Atwater consistency
        when an item is not present in the indexed database.
        """
        name_l = name.lower()
        if any(k in name_l for k in ["rice", "chawal", "pulao", "biryani", "khichdi", "grain"]):
            category = "Rice Dishes"
            p, c, f, fib, port = 3.0, 26.0, 3.5, 1.5, 180.0
        elif any(k in name_l for k in ["roti", "paratha", "naan", "bread", "puri", "kulcha", "dosa", "idli", "flatbread"]):
            category = "Breads"
            p, c, f, fib, port = 7.0, 45.0, 10.0, 4.0, 80.0
        elif any(k in name_l for k in ["dal", "lentil", "sambar", "chole", "rajma", "shorba", "rasam"]):
            category = "Dals and Lentils"
            p, c, f, fib, port = 6.5, 15.0, 4.0, 4.5, 150.0
        elif any(k in name_l for k in ["paneer", "chicken", "mutton", "fish", "egg", "meat", "curry", "gravy", "tikka"]):
            category = "Curries"
            p, c, f, fib, port = 12.0, 8.0, 14.0, 1.5, 160.0
        elif any(k in name_l for k in ["sweet", "halwa", "laddu", "jamun", "kheer", "barfi", "dessert", "mithai"]):
            category = "Sweets"
            p, c, f, fib, port = 5.0, 55.0, 18.0, 1.0, 50.0
        elif any(k in name_l for k in ["tea", "chai", "coffee", "lassi", "juice", "drink", "beverage"]):
            category = "Beverages"
            p, c, f, fib, port = 2.0, 10.0, 2.5, 0.1, 150.0
        else:
            category = "General Indian Dish"
            p, c, f, fib, port = 5.0, 20.0, 7.0, 2.5, 150.0

        cal = round(4.0 * p + 4.0 * c + 9.0 * f, 1)
        return FoodRecord(
            food_id=f"IF_EST_{uuid.uuid4().hex[:6]}",
            food_name=name.title(),
            aliases=[name.lower()],
            category=category,
            calories_100g=cal,
            protein_100g=p,
            carbs_100g=c,
            fat_100g=f,
            fiber_100g=fib,
            default_portion_g=port,
            source="ESTIMATED_FALLBACK",
            notes="Dynamic culinary profile generated for unindexed item with Atwater verification",
        )



if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Ensure project root is in sys.path so direct execution works
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from backend.app.vision.mock_detector import MockVisionModel
    from backend.app.rag.pipeline import RAGPipeline

    print("=" * 60)
    print("DietAI24 -- Testing AnalysisService Pipeline Locally")
    print("=" * 60)

    print("1. Initializing Mock Vision Model & FAISS RAG Pipeline...")
    vision = MockVisionModel()
    rag = RAGPipeline(data_dir=str(project_root / "data"))
    rag.load_or_build()

    service = AnalysisService(vision_model=vision, rag_pipeline=rag)

    print("2. Running complete pipeline on sample meal image...")
    sample_img = project_root / "frontend" / "src" / "assets" / "hero.png"
    result = service.analyze_image(str(sample_img) if sample_img.exists() else "dosa.jpg", debug=True)

    print(f"\nStatus: {result.status.upper()} (Analysis ID: {result.analysis_id})")
    print(f"Total Foods Identified: {result.food_count}")
    print("-" * 60)
    for item in result.foods:
        print(
            f"  * {item.standardized_name:<20} "
            f"[{item.portion.size_label} | {item.portion.estimated_grams:4.0f}g] "
            f"-> {item.nutrition.calories_kcal:5.1f} kcal "
            f"(P: {item.nutrition.protein_g:4.1f}g, C: {item.nutrition.carbs_g:4.1f}g, F: {item.nutrition.fat_g:4.1f}g)"
        )
    print("-" * 60)
    if result.totals:
        print(
            f"TOTAL MEAL NUTRITION: {result.totals.calories_kcal:.1f} kcal | "
            f"Weight: {result.totals.total_weight_g:.0f}g"
        )
        split = result.totals.macro_split
        print(
            f"Macro Split: Protein: {split['protein_pct']}% | Carbs: {split['carbs_pct']}% | Fat: {split['fat_pct']}%"
        )
    print("=" * 60)

