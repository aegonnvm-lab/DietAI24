# DietAI24 Architecture Specification

## Overview

DietAI24 is an academic and research-oriented AI application that estimates the nutritional content of Indian and global meals from photographs. It solves the critical vulnerability present in standard end-to-end Vision-Language Models (VLMs): **hallucinated nutrition, forced nearest-vector substitutions, and arithmetic drift**.

Instead of treating the nutrition database as the vision classifier, DietAI24 strictly separates:
1. **Visual Recognition** (Spatial multi-food detection, bounding box proposals, and per-region classification)
2. **Food Normalization** (Lexical cleanup and alias resolution)
3. **Nutrition Retrieval** (Grounded semantic vector search with anti-false-positive category gating)
4. **Portion Estimation** (Instance counting, visual mass cues, and container scaling)
5. **Deterministic Calculation** (Physical Atwater arithmetic: $4P + 4C + 9F$)

---

## Decoupled Architecture Flow

```
                MEAL IMAGE
                    ↓
             FOOD DETECTOR
                    ↓
          MULTI-FOOD REGIONS
                    ↓
          SEGMENTATION / MASKS
                    ↓
          FOOD CLASSIFICATION
                    ↓
          FOOD NORMALIZATION
                    ↓
            EMBEDDINGS
                    ↓
             VECTOR SEARCH
                    ↓
        NUTRITION KNOWLEDGE BASE
                    ↓
           PORTION ESTIMATION
                    ↓
        DETERMINISTIC CALCULATION
                    ↓
          MEAL TOTALS + UI
```

---

## Critical Distinction: Vision Datasets vs. Nutrition Datasets

A fundamental architectural principle of DietAI24 is the **strict separation between vision data and nutrition data**:

| Property | Vision Datasets | Nutrition Knowledge Bases |
| :--- | :--- | :--- |
| **Primary Purpose** | Teaching neural networks to localize and identify food patterns visually. | Providing laboratory-verified biochemical nutritional composition. |
| **Typical Sources** | Food-101, UEC-Food256, Nutrition5k, ImageNet food subsets. | IFCT 2017 (ICMR-NIN), USDA FoodData Central. |
| **Data Types** | RGB images, bounding boxes, segmentation masks, category tags. | Moisture, protein, lipids, dietary fiber, ash, micronutrients per 100g. |
| **Common Trap Avoided** | **Never assume image tags contain trustworthy nutrition values.** | **Never use nutrition records as an image classifier.** |

A visually similar food must **never** automatically become the retrieved database food simply because embeddings are adjacent in high-dimensional vector space. For example: **an Omelette must never resolve to Yellow Dal Tadka**.

---

## Multi-Stage Vision & Retrieval Pipeline

### Stage 1: Spatial Candidate Region Proposal & Detection
- **Interface:** `backend.app.vision.interfaces.FoodDetector`
- **Responsibility:** Proposes localized bounding boxes `[ymin, xmin, ymax, xmax]` and instance counts (e.g. 2 rotis, 3 idlis, 1 omelette).
- **Implementations:**
  - `MockVisionModel`: Generates deterministic multi-food plates (e.g. 6-item Thali, Omelette, Dosa) with normalized bounding boxes and visual cues.
  - `GeminiVisionModel` / `ClaudeVisionModel`: Multimodal structured prompts returning bounding boxes and counts.

### Stage 2: Individual Food Classification
- **Interface:** `backend.app.vision.interfaces.FoodClassifier`
- **Responsibility:** Classifies each localized crop independently rather than assigning a single whole-image label.

### Stage 3: Strict Anti-False-Positive Normalization & Matching
- **Module:** `backend.app.rag.matcher.StrictFoodMatcher`
- **Rules:**
  1. **Lexical / Alias Matching:** Resolves synonyms (*omelet* $\rightarrow$ *Plain Omelette*, *chawal* $\rightarrow$ *Steamed White Rice*).
  2. **Category Incompatibility Gating:** Explicitly blocks absurd vector substitutions (e.g. Eggs cannot resolve to Dals & Lentils; Breads cannot resolve to Beverages).
  3. **Multi-Tier Confidence Thresholds:**
     - $\ge 0.72$: High Confidence (`HIGH_CONFIDENCE`)
     - $0.50 - 0.71$: Medium Confidence with category check (`MEDIUM_CONFIDENCE`)
     - $< 0.50$: Explicit Refusal (`NUTRITION_UNAVAILABLE`)
  4. **Uncertainty Refusal:** Low visual confidence ($< 0.40$) returns `LOW_CONFIDENCE` with user verification flags rather than guessing.

### Stage 4: Portion Estimation & Instance Scaling
- **Module:** `backend.app.nutrition.portion`
- **Logic:** Scales default portion weight by instance count ($W_{\text{total}} = W_{\text{base}} \times \text{count}$). Incorporates container scale (katori vs. plate vs. bowl).
- **Transparency:** Always flags output as *"Estimated portion"* until user confirms or overrides.

### Stage 5: Deterministic Physical Calculation
- **Module:** `backend.app.nutrition.calculator`
- **Arithmetic:**
  $$\text{Calories} = \left(\text{Protein} \times 4 + \text{Carbs} \times 4 + \text{Fat} \times 9\right) \times \frac{\text{grams}}{100}$$
  $$\text{Total Meal} = \sum_{i=1}^{N} \text{Food}_i$$
- Guaranteed mathematical determinism with zero LLM arithmetic hallucination.

---

## Interactive Frontend Visualization
- **SVG Bounding Box Layer:** Dynamic SVG overlays synchronized over the meal image preview.
- **Instance Count Indicators:** Displays `Roti × 2`, `Idli × 3`, `1 Omelette`.
- **Food Breakdown Table:** Itemized comparison of Food Name, Count, Portion, Energy, Macros, and Retrieval Confidence.
- **Visual Debug Mode:** Step-by-step diagnostic breakdown covering Image Validation $\rightarrow$ Regions $\rightarrow$ Classification $\rightarrow$ Anti-False-Positive RAG $\rightarrow$ Portions $\rightarrow$ Atwater Calculation.
