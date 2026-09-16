import React from 'react';

export default function Methodology() {
  return (
    <div className="methodology-container" id="methodology-container">
      <div className="methodology-header">
        <h2>DietAI24 Research Architecture & Methodology</h2>
        <p>
          An academic AI framework designed to overcome Large Multimodal Model (LMM) arithmetic
          hallucinations in dietary assessment through Grounded Vector Retrieval (FAISS RAG).
        </p>
      </div>

      {/* Core Paradigm Comparison */}
      <div className="paradigm-grid">
        <div className="paradigm-card old-way glass-panel">
          <div className="paradigm-icon">❌</div>
          <h3>Traditional End-to-End LLM Prompting</h3>
          <p className="paradigm-desc">
            Directly asking an LLM: <em>"How many calories are in this meal photo?"</em>
          </p>
          <ul className="paradigm-list">
            <li><strong>Severe Hallucination:</strong> Calorie estimates drift by ±60% across identical prompts.</li>
            <li><strong>Opaque Arithmetic:</strong> Macro numbers do not sum to total caloric energy (4/4/9 rule violated).</li>
            <li><strong>Lack of Ground Truth:</strong> Model relies on vague parametric memory instead of Indian food tables.</li>
          </ul>
        </div>

        <div className="paradigm-card new-way glass-panel">
          <div className="paradigm-icon">✅</div>
          <h3>DietAI24 Grounded RAG Architecture</h3>
          <p className="paradigm-desc">
            Decoupled perception, retrieval, and deterministic computation.
          </p>
          <ul className="paradigm-list">
            <li><strong>Vision For Perception Only:</strong> VLM identifies visual entities ("roti", "dal").</li>
            <li><strong>FAISS Vector Retrieval:</strong> Standardizes names against verified Indian food records.</li>
            <li><strong>Deterministic Python Math:</strong> Calories = (weight / 100) × standard_calories. Zero hallucination.</li>
          </ul>
        </div>
      </div>

      {/* 5-Stage Pipeline Flow */}
      <div className="pipeline-breakdown-card glass-panel" id="pipeline-breakdown">
        <h3>The 5-Stage DietAI24 Pipeline</h3>
        <div className="stages-flow-list">
          <div className="stage-block">
            <div className="stage-badge">Stage 1</div>
            <h4>Visual Recognition (VLM)</h4>
            <p>
              Accepts meal photograph and extracts candidate food names, boundary regions,
              and visual confidence scores using Vision-Language Models (Claude 3.5 Sonnet or Mock).
            </p>
          </div>

          <div className="stage-block">
            <div className="stage-badge">Stage 2</div>
            <h4>Text Normalization & Alias Mapping</h4>
            <p>
              Pre-processes colloquial Indian food names, regional spellings (e.g. <em>"chawal" → "steamed rice"</em>,
              <em>"biriyani" → "biryani"</em>) across 180+ curated aliases.
            </p>
          </div>

          <div className="stage-block">
            <div className="stage-badge">Stage 3</div>
            <h4>FAISS Semantic Retrieval (RAG)</h4>
            <p>
              Dense embeddings generated with <code>all-MiniLM-L6-v2</code> (384-dimensions) queried
              against an indexed vector store of Indian food composition data with L2 distance ranking.
            </p>
          </div>

          <div className="stage-block">
            <div className="stage-badge">Stage 4</div>
            <h4>Portion Estimation (Rule-Based + Override)</h4>
            <p>
              Initializes empirical standard serving weights by category (e.g., bowl of dal: 150g,
              roti: 35g), while empowering the user with interactive sliders for immediate correction.
            </p>
          </div>

          <div className="stage-block">
            <div className="stage-badge">Stage 5</div>
            <h4>Deterministic Macro Calculation</h4>
            <p>
              Computes calories, macronutrients (Protein, Carbs, Fat, Fiber), and percentage macro splits
              using standard Atwater factors (4 kcal/g protein, 4 kcal/g carbs, 9 kcal/g fat).
            </p>
          </div>
        </div>
      </div>

      {/* Research Roadmap / Milestone Progression */}
      <div className="roadmap-section glass-panel" id="research-roadmap">
        <h3>Research Roadmap: Milestone 1 → Future Extensions</h3>
        <div className="roadmap-grid">
          <div className="roadmap-item current">
            <span className="roadmap-status">Milestone 1 (Current MVP)</span>
            <h4>Modular Prototype</h4>
            <p>
              Single top-down photo, FAISS index, rule-based portion sizes, interactive human-in-the-loop
              corrections, and verified database grounding.
            </p>
          </div>

          <div className="roadmap-item future">
            <span className="roadmap-status">Future Milestone 2</span>
            <h4>3D Mesh & Depth Sizing</h4>
            <p>
              Smartphone LiDAR or multi-view depth maps to reconstruct food volume in cm³ and density
              matrices (g/cm³) for automated gram estimation.
            </p>
          </div>

          <div className="roadmap-item future">
            <span className="roadmap-status">Future Milestone 3</span>
            <h4>Personalized Metabolic Sync</h4>
            <p>
              Integration with continuous glucose monitors (CGM), BMR/TDEE calculations, and regional
              recipe variations (oil/ghee adjustments).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
