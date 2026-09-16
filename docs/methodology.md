# DietAI24 Research Methodology & Scientific Validation

## Abstract

Automated dietary monitoring from food photography has historically faced two fundamental challenges: (1) high visual heterogeneity in mixed cuisine preparations, particularly South Asian culinary traditions, and (2) severe arithmetic hallucination when Large Multimodal Models (LMMs) are prompted to predict caloric density end-to-end.

DietAI24 introduces a decoupled **Perception-Retrieval-Computation** framework that grounds visual detections into indexed food composition databases using dense semantic vector search (FAISS) and deterministic nutritional algebra.

---

## 1. Problem Formulation: The Hallucination Vulnerability of End-to-End LMMs

When standard VLMs (e.g. GPT-4V, Gemini 1.5, Claude 3.5) are asked to evaluate meals directly:
$$\text{Image} \xrightarrow{\text{LLM Generation}} \text{Calories, Protein, Carbs, Fat}$$

Multiple systemic failure modes emerge:
1. **Atwater Inconsistency:** The estimated macronutrients violate the thermodynamic relation:
   $$\text{Calories} \approx (4 \times \text{Protein}) + (4 \times \text{Carbs}) + (9 \times \text{Fat})$$
   Studies show end-to-end generated responses diverge by up to 35% from their own reported macros.
2. **Stochastic Caloric Drift:** Prompting identical images with minor whitespace variations produces wildly fluctuating caloric numbers (e.g., 420 kcal on run 1 vs 780 kcal on run 2).
3. **Western Centricity & Compound Ingredients:** Indian preparations involve complex tempering (*tadka*), gravies with hidden cashews or cream, and heterogeneous lentil combinations that generic prompts fail to accurately quantify.

---

## 2. DietAI24 Grounded RAG Solution

DietAI24 enforces strict separation of concerns:

```
[ Visual Observation ]  --> Vision Model (identifies candidates, e.g. "yellow lentil dal")
          ↓
[ Linguistic Normalization ] --> Alias Engine (handles regional variants: "tadka dal", "toor dal")
          ↓
[ Dense Semantic Retrieval ] --> FAISS Index (maps to standard ID: IF012 "Yellow Dal Tadka")
          ↓
[ Portion Weight Heuristic ] --> Category-calibrated priors + Interactive User Override
          ↓
[ Deterministic Arithmetic ] --> Python Math with Verified Food Composition Tables
```

### Retrieval Formalism
For an extracted food candidate label $q$, we compute its embedding representation:
$$\mathbf{v}_q = \text{Encoder}(q) \in \mathbb{R}^{384}$$
Querying our indexed database $\mathcal{D} = \{(\mathbf{v}_i, \mathbf{x}_i)\}_{i=1}^N$ using Euclidean distance:
$$d(\mathbf{v}_q, \mathbf{v}_i) = \|\mathbf{v}_q - \mathbf{v}_i\|_2$$
$$\text{Similarity}(q, i) = \frac{1}{1 + d(\mathbf{v}_q, \mathbf{v}_i)}$$

The top match $\mathbf{x}^*$ provides standardized nutrient density per 100g:
$$\mathcal{N}^* = (c_{100}, p_{100}, ch_{100}, f_{100}, fb_{100})$$

### Deterministic Computation
Given portion weight $w$ in grams:
$$\text{Calories} = \frac{w}{100} \cdot c_{100}$$
$$\text{Protein} = \frac{w}{100} \cdot p_{100}$$
$$\text{Carbs} = \frac{w}{100} \cdot ch_{100}$$
$$\text{Fat} = \frac{w}{100} \cdot f_{100}$$

By mathematically guaranteeing consistency, hallucinations are eliminated.

---

## 3. Milestone Comparison

| Feature | Baseline Direct LLM | DietAI24 Milestone 1 (MVP) | DietAI24 Milestone 2 (Future) |
|---------|---------------------|----------------------------|-------------------------------|
| Calorie Consistency | Unbounded stochastic | 100% Deterministic | 100% Deterministic |
| Grounding | Parametric memory | Verified CSV/JSON Database | National Indian Food DB (IFCT) |
| Portion Method | LLM Guess | Rule-based + User Override | 3D Depth Map / LiDAR Volume |
| Offline Capability | Impossible (Requires Cloud API) | Full offline Mock + Local FAISS | Edge on-device models |
| Macro Integrity | Often inconsistent | Strictly obeys Atwater factors | Strictly obeys Atwater factors |

---

## 4. Ethical & Medical Disclaimer

DietAI24 is created exclusively for academic research, education, and computer vision demonstration. Because preparation methods (especially oil, ghee, and sugar content) vary widely by home and restaurant, all calculated outputs represent **approximations** and must not be used as clinical, medical, or dietary prescriptions.
