import React, { useState, useRef } from 'react';
import { analyzeMealImage, recalculateNutrition } from '../services/api';

// Curated palette for multi-food bounding boxes
const BBOX_COLORS = ['#10b981', '#f59e0b', '#06b6d4', '#ec4899', '#8b5cf6', '#3b82f6', '#14b8a6'];

// Sample presets for 1-click test scenarios
const SAMPLE_PRESETS = [
  {
    id: 'omelette',
    name: 'Plain Omelette',
    desc: 'Omelette Recognition Test (NOT Dal Tadka)',
    emoji: '🍳',
    color: '#f59e0b',
  },
  {
    id: 'thali',
    name: 'North Indian Thali (6 Foods)',
    desc: 'Rice, Dal, Paneer, Roti x2, Salad, Curd',
    emoji: '🍱',
    color: '#10b981',
  },
  {
    id: 'dosa',
    name: 'South Indian Breakfast',
    desc: 'Masala Dosa, Sambar, Chutney',
    emoji: '🥞',
    color: '#06b6d4',
  },
  {
    id: 'samosa',
    name: '2 Samosas & Chai',
    desc: 'Instance Counting Test (2 Samosas)',
    emoji: '🥟',
    color: '#ec4899',
  },
  {
    id: 'biryani',
    name: 'Chicken Biryani Feast',
    desc: 'Biryani, Raita, Salad',
    emoji: '🍗',
    color: '#f43f5e',
  },
  {
    id: 'unknown',
    name: 'Ambiguous / Low-Confidence',
    desc: 'Anti-False-Positive Refusal Test',
    emoji: '❓',
    color: '#64748b',
  },
];

// Helper to create a dummy image blob for preset testing
function createPresetBlob(label, color = '#f59e0b') {
  const canvas = document.createElement('canvas');
  canvas.width = 400;
  canvas.height = 300;
  const ctx = canvas.getContext('2d');

  // Background gradient
  const grad = ctx.createLinearGradient(0, 0, 400, 300);
  grad.addColorStop(0, '#1a2233');
  grad.addColorStop(1, '#0b0f17');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 400, 300);

  // Border ring
  ctx.strokeStyle = color;
  ctx.lineWidth = 4;
  ctx.strokeRect(16, 16, 368, 268);

  // Text
  ctx.fillStyle = '#f8fafc';
  ctx.font = 'bold 22px Outfit, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(label, 200, 135);

  ctx.fillStyle = '#94a3b8';
  ctx.font = '13px sans-serif';
  ctx.fillText('Multi-Food Vision & RAG Verification', 200, 168);

  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob), 'image/jpeg');
  });
}

export default function MealAnalysis() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [pipelineStage, setPipelineStage] = useState(0);
  const [error, setError] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [recalculating, setRecalculating] = useState(false);
  const [showDebug, setShowDebug] = useState(false);
  const [selectedFoodId, setSelectedFoodId] = useState(null);

  // Local state for editable portions
  const [editedPortions, setEditedPortions] = useState({});

  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      processSelectedFile(file);
    }
  };

  const processSelectedFile = (file) => {
    setSelectedFile(file);
    setError(null);
    setAnalysisResult(null);
    setSelectedFoodId(null);

    const reader = new FileReader();
    reader.onload = () => {
      setPreviewUrl(reader.result);
    };
    reader.readAsDataURL(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith('image/')) {
      processSelectedFile(file);
    }
  };

  const handleSelectPreset = async (preset) => {
    setError(null);
    const blob = await createPresetBlob(preset.name, preset.color);
    const file = new File([blob], `${preset.id}_preset.jpg`, { type: 'image/jpeg' });
    processSelectedFile(file);
  };

  const handleClear = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setAnalysisResult(null);
    setSelectedFoodId(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const runAnalysis = async () => {
    if (!selectedFile) return;

    setLoading(true);
    setError(null);
    setPipelineStage(1);

    // Visual progression simulation for pipeline steps
    const stageTimer1 = setTimeout(() => setPipelineStage(2), 500);
    const stageTimer2 = setTimeout(() => setPipelineStage(3), 1000);
    const stageTimer3 = setTimeout(() => setPipelineStage(4), 1500);

    try {
      const data = await analyzeMealImage(selectedFile, true);
      setPipelineStage(5);
      setAnalysisResult(data);

      if (data.foods && data.foods.length > 0) {
        setSelectedFoodId(data.foods[0].instance_id || data.foods[0].food_id);
      }

      // Initialize edited portions from result
      const initialPortions = {};
      if (data.foods) {
        data.foods.forEach((item) => {
          initialPortions[item.food_id] = item.portion.estimated_grams;
        });
      }
      setEditedPortions(initialPortions);
    } catch (err) {
      setError(err.message || 'Failed to analyze meal image. Please try again.');
    } finally {
      clearTimeout(stageTimer1);
      clearTimeout(stageTimer2);
      clearTimeout(stageTimer3);
      setLoading(false);
    }
  };

  const handlePortionChange = (foodId, value) => {
    const parsed = parseFloat(value);
    setEditedPortions((prev) => ({
      ...prev,
      [foodId]: isNaN(parsed) ? 0 : parsed,
    }));
  };

  const applyPortionPreset = (foodId, multiplier) => {
    const currentItem = analysisResult?.foods?.find((f) => f.food_id === foodId);
    if (!currentItem) return;
    const baseGrams = currentItem.portion.estimated_grams;
    const newGrams = Math.round(baseGrams * multiplier);
    handlePortionChange(foodId, newGrams);
  };

  const handleRecalculate = async () => {
    if (!analysisResult || !analysisResult.foods) return;

    setRecalculating(true);
    try {
      const corrections = analysisResult.foods.map((item) => ({
        food_id: item.food_id,
        food_name: item.standardized_name,
        grams: editedPortions[item.food_id] ?? item.portion.estimated_grams,
      }));

      const updated = await recalculateNutrition(corrections);
      setAnalysisResult((prev) => ({
        ...prev,
        totals: updated.totals,
        foods: updated.foods.map((f, i) => ({
          ...prev.foods[i],
          portion: f.portion,
          nutrition: f.nutrition,
        })),
      }));
    } catch (err) {
      setError('Recalculation error: ' + err.message);
    } finally {
      setRecalculating(false);
    }
  };

  return (
    <div className="meal-analysis-view">
      {/* Hero Section */}
      <section className="analysis-hero">
        <h1 className="hero-heading">Multi-Food Vision & Nutrition Intelligence</h1>
        <p className="hero-subtext">
          Decoupled AI vision architecture: Spatial bounding box detection → individual food classification →
          strict anti-false-positive RAG normalization → deterministic nutrition calculation.
        </p>
      </section>

      {/* Preset Quick-Test Chips */}
      <div className="presets-bar" id="presets-bar">
        <span className="presets-label">⚡ Test Scenarios:</span>
        <div className="presets-list">
          {SAMPLE_PRESETS.map((p) => (
            <button
              key={p.id}
              className="preset-chip"
              onClick={() => handleSelectPreset(p)}
              title={p.desc}
              id={`preset-btn-${p.id}`}
            >
              <span className="preset-emoji">{p.emoji}</span>
              <span className="preset-name">{p.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Upload + Pipeline Controller Grid */}
      <div className="upload-section-grid">
        {/* Upload Card / Preview */}
        <div
          className={`upload-card glass-panel ${previewUrl ? 'has-preview' : ''}`}
          id="upload-card"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => !previewUrl && fileInputRef.current?.click()}
        >
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: 'none' }}
            accept="image/*"
            onChange={handleFileChange}
            id="meal-image-input"
          />

          {!previewUrl ? (
            <div className="dropzone-content" id="dropzone-content">
              <div className="upload-icon-circle">
                <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
              </div>
              <h3 className="upload-prompt-title">Drop your meal photo here</h3>
              <p className="upload-prompt-desc">Upload a single food (e.g. Omelette) or multi-food thali plate</p>
              <button
                type="button"
                id="btn-browse-file"
                className="btn-primary browse-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  fileInputRef.current?.click();
                }}
              >
                Browse Image
              </button>
            </div>
          ) : (
            <div className="detection-overlay-wrapper" id="detection-overlay-wrapper">
              <img
                src={previewUrl}
                alt="Meal Preview"
                className="preview-image"
                id="meal-preview-img"
                style={{ maxHeight: '360px', width: '100%', objectFit: 'contain' }}
              />

              {/* Interactive Multi-Food SVG Overlays */}
              {analysisResult?.foods && (
                <svg
                  className="detection-svg-overlay"
                  viewBox="0 0 100 100"
                  preserveAspectRatio="none"
                  id="detection-svg-canvas"
                >
                  {analysisResult.foods.map((food, i) => {
                    const bbox = food.detection?.bbox || food.bounding_box;
                    if (!bbox) return null;
                    const ymin = (bbox.ymin ?? 0) * 100;
                    const xmin = (bbox.xmin ?? 0) * 100;
                    const ymax = (bbox.ymax ?? 1) * 100;
                    const xmax = (bbox.xmax ?? 1) * 100;
                    const width = Math.max(3, xmax - xmin);
                    const height = Math.max(3, ymax - ymin);
                    const isSelected = selectedFoodId === (food.instance_id || food.food_id);
                    const color = BBOX_COLORS[i % BBOX_COLORS.length];

                    return (
                      <g
                        key={food.instance_id || i}
                        className={`bbox-group ${isSelected ? 'selected' : ''}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedFoodId(food.instance_id || food.food_id);
                          const el = document.getElementById(`food-card-${food.food_id || food.instance_id}`);
                          if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        }}
                      >
                        <rect
                          className="bbox-rect"
                          x={xmin}
                          y={ymin}
                          width={width}
                          height={height}
                          fill={isSelected ? `${color}45` : `${color}1a`}
                          stroke={isSelected ? '#ffffff' : color}
                          strokeWidth={isSelected ? '0.9' : '0.45'}
                          strokeDasharray={isSelected ? '2,1' : 'none'}
                          rx="1"
                        />
                        {/* Region Tag Pill */}
                        <rect
                          x={xmin}
                          y={Math.max(0, ymin - 4.2)}
                          width={Math.min(width, 42)}
                          height="4"
                          fill={color}
                          rx="0.8"
                        />
                        <text
                          x={xmin + 1}
                          y={Math.max(2.8, ymin - 1.2)}
                          fill="#ffffff"
                          fontSize="2.4"
                          fontWeight="bold"
                          fontFamily="Outfit, sans-serif"
                        >
                          {food.count > 1 ? `${food.standardized_name} ×${food.count}` : food.standardized_name}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              )}

              <div className="preview-overlay">
                <span className="preview-filename">{selectedFile?.name}</span>
                <button
                  id="btn-clear-image"
                  className="btn-clear"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleClear();
                  }}
                  title="Remove image"
                >
                  ✕ Clear
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Action & Status Card */}
        <div className="action-card glass-panel" id="action-card">
          <div className="action-card-header">
            <h3>Pipeline Controller</h3>
            <span className="stage-pill">
              {loading ? `Phase ${pipelineStage}/4 Processing` : analysisResult ? 'Analysis Ready' : 'Awaiting Input'}
            </span>
          </div>

          <p className="action-card-desc">
            Decoupled Vision $\rightarrow$ Normalization $\rightarrow$ Retrieval $\rightarrow$ Calculation.
            Never substitutes an Omelette with Dal Tadka.
          </p>

          {/* Pipeline Stage Indicators */}
          <div className="pipeline-steps-tracker" id="pipeline-steps-tracker">
            <div className={`step-item ${pipelineStage >= 1 ? 'active' : ''} ${pipelineStage > 1 ? 'done' : ''}`}>
              <span className="step-num">1</span>
              <span className="step-label">Multi-Region Vision</span>
            </div>
            <div className={`step-item ${pipelineStage >= 2 ? 'active' : ''} ${pipelineStage > 2 ? 'done' : ''}`}>
              <span className="step-num">2</span>
              <span className="step-label">Anti-FP Matcher</span>
            </div>
            <div className={`step-item ${pipelineStage >= 3 ? 'active' : ''} ${pipelineStage > 3 ? 'done' : ''}`}>
              <span className="step-num">3</span>
              <span className="step-label">Instance Counting</span>
            </div>
            <div className={`step-item ${pipelineStage >= 4 ? 'active' : ''} ${pipelineStage >= 5 ? 'done' : ''}`}>
              <span className="step-num">4</span>
              <span className="step-label">Deterministic Math</span>
            </div>
          </div>

          {/* Action Trigger Button */}
          <div className="action-btn-row">
            <button
              id="btn-run-analysis"
              className="btn-primary analyze-submit-btn"
              disabled={!selectedFile || loading}
              onClick={runAnalysis}
            >
              {loading ? (
                <>
                  <span className="spinner"></span>
                  <span>Executing Pipeline...</span>
                </>
              ) : (
                <>
                  <span>⚡ Analyze Meal & Estimate</span>
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="error-banner" id="error-banner">
              <strong>Error:</strong> {error}
            </div>
          )}
        </div>
      </div>

      {/* Results Section */}
      {analysisResult && (
        <section className="results-section animate-fade-in" id="results-section">
          {/* Section Header */}
          <div className="results-header-row">
            <div>
              <h2 className="results-title">Estimated Nutrition Summary</h2>
              <span className="analysis-id-tag">
                ID: {analysisResult.analysis_id} • Mode: {analysisResult.vision_mode?.toUpperCase()}
              </span>
            </div>
            <div className="results-actions-row">
              <button
                id="btn-toggle-debug"
                className={`btn-secondary ${showDebug ? 'active' : ''}`}
                onClick={() => setShowDebug(!showDebug)}
              >
                {showDebug ? 'Hide Visual Debug Mode' : '🔍 Show Visual Debug Mode'}
              </button>
            </div>
          </div>

          {/* Uncertainty / Quality Warnings */}
          {analysisResult.warnings && analysisResult.warnings.length > 0 && (
            <div className="uncertainty-warnings-container" id="uncertainty-warnings">
              {analysisResult.warnings.map((w, idx) => (
                <div key={idx} className="uncertainty-warning-banner">
                  <span>⚠️</span>
                  <span>{w}</span>
                </div>
              ))}
            </div>
          )}

          {/* Hero Totals Grid */}
          <div className="totals-hero-grid" id="totals-hero-grid">
            <div className="total-stat-card primary-calorie-card">
              <span className="stat-label">Total Meal Energy</span>
              <div className="stat-value-group">
                <span className="stat-value-large" id="total-calories-val">
                  {Math.round(analysisResult.totals?.calories_kcal || 0)}
                </span>
                <span className="stat-unit">kcal</span>
              </div>
              <span className="stat-hint">
                Across {analysisResult.foods.length} detected food {analysisResult.foods.length === 1 ? 'item' : 'items'}
              </span>
            </div>

            <div className="total-stat-card">
              <span className="stat-label">Total Protein</span>
              <div className="stat-value-group">
                <span className="stat-value" id="total-protein-val">
                  {(analysisResult.totals?.protein_g || 0).toFixed(1)}
                </span>
                <span className="stat-unit">g</span>
              </div>
              <span className="stat-sub">
                {analysisResult.totals?.macro_split?.protein_pct?.toFixed(0) || 0}% of energy
              </span>
            </div>

            <div className="total-stat-card">
              <span className="stat-label">Total Carbohydrates</span>
              <div className="stat-value-group">
                <span className="stat-value" id="total-carbs-val">
                  {(analysisResult.totals?.carbs_g || 0).toFixed(1)}
                </span>
                <span className="stat-unit">g</span>
              </div>
              <span className="stat-sub">
                {analysisResult.totals?.macro_split?.carbs_pct?.toFixed(0) || 0}% of energy
              </span>
            </div>

            <div className="total-stat-card">
              <span className="stat-label">Total Fat</span>
              <div className="stat-value-group">
                <span className="stat-value" id="total-fat-val">
                  {(analysisResult.totals?.fat_g || 0).toFixed(1)}
                </span>
                <span className="stat-unit">g</span>
              </div>
              <span className="stat-sub">
                {analysisResult.totals?.macro_split?.fat_pct?.toFixed(0) || 0}% of energy
              </span>
            </div>

            <div className="total-stat-card">
              <span className="stat-label">Estimated Meal Weight</span>
              <div className="stat-value-group">
                <span className="stat-value" id="total-weight-val">
                  {Math.round(analysisResult.totals?.total_weight_g || 0)}
                </span>
                <span className="stat-unit">g</span>
              </div>
              <span className="stat-sub">
                Fiber: {(analysisResult.totals?.fiber_g || 0).toFixed(1)}g
              </span>
            </div>
          </div>

          {/* Macro Split Progress Bar */}
          <div className="macro-progress-card glass-panel" id="macro-split-bar">
            <div className="macro-labels-row">
              <span className="macro-legend protein">
                ● Protein: {analysisResult.totals?.macro_split?.protein_pct?.toFixed(1)}%
              </span>
              <span className="macro-legend carbs">
                ● Carbs: {analysisResult.totals?.macro_split?.carbs_pct?.toFixed(1)}%
              </span>
              <span className="macro-legend fat">
                ● Fat: {analysisResult.totals?.macro_split?.fat_pct?.toFixed(1)}%
              </span>
            </div>
            <div className="macro-multi-bar">
              <div
                className="bar-segment protein"
                style={{ width: `${analysisResult.totals?.macro_split?.protein_pct || 0}%` }}
              ></div>
              <div
                className="bar-segment carbs"
                style={{ width: `${analysisResult.totals?.macro_split?.carbs_pct || 0}%` }}
              ></div>
              <div
                className="bar-segment fat"
                style={{ width: `${analysisResult.totals?.macro_split?.fat_pct || 0}%` }}
              ></div>
            </div>
          </div>

          {/* Food Breakdown Summary Table */}
          <div className="breakdown-table-wrapper" id="breakdown-table-wrapper">
            <table className="breakdown-table">
              <thead>
                <tr>
                  <th>Detected Food Item</th>
                  <th>Visual Count</th>
                  <th>Portion Weight</th>
                  <th>Total Energy</th>
                  <th>Macro Breakdown (P / C / F)</th>
                  <th>Match Confidence</th>
                </tr>
              </thead>
              <tbody>
                {analysisResult.foods.map((food, idx) => {
                  const isSelected = selectedFoodId === (food.instance_id || food.food_id);
                  return (
                    <tr
                      key={food.instance_id || idx}
                      style={{
                        cursor: 'pointer',
                        background: isSelected ? 'rgba(245, 158, 11, 0.08)' : 'transparent',
                      }}
                      onClick={() => {
                        setSelectedFoodId(food.instance_id || food.food_id);
                        const el = document.getElementById(`food-card-${food.food_id || food.instance_id}`);
                        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                      }}
                    >
                      <td>
                        <strong>{food.standardized_name}</strong>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                          Detected: "{food.detected_name}"
                        </div>
                      </td>
                      <td>
                        <span className="count-badge-pill">
                          {food.count > 1 ? `${food.count} items` : '1 item'}
                        </span>
                      </td>
                      <td>{Math.round(editedPortions[food.food_id] ?? food.portion.estimated_grams)} g</td>
                      <td>
                        <span style={{ color: 'var(--saffron-400)', fontWeight: 700 }}>
                          {Math.round(food.nutrition.calories_kcal)} kcal
                        </span>
                      </td>
                      <td>
                        {food.nutrition.protein_g.toFixed(1)}g P / {food.nutrition.carbs_g.toFixed(1)}g C /{' '}
                        {food.nutrition.fat_g.toFixed(1)}g F
                      </td>
                      <td>
                        <span className={`confidence-pill ${food.retrieval_confidence}`}>
                          {food.match_status || food.retrieval_confidence.toUpperCase()} (
                          {Math.round(food.retrieval_score * 100)}%)
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Detected Food Detail Cards */}
          <div className="detected-foods-header-row">
            <h3>Detected Food Items ({analysisResult.foods.length})</h3>
            <button
              id="btn-recalculate-all"
              className="btn-primary recalculate-btn"
              disabled={recalculating}
              onClick={handleRecalculate}
            >
              {recalculating ? 'Recalculating...' : '🔄 Recalculate with Custom Portions'}
            </button>
          </div>

          <div className="foods-cards-list" id="detected-foods-list">
            {analysisResult.foods.map((food, idx) => {
              const isSelected = selectedFoodId === (food.instance_id || food.food_id);
              return (
                <div
                  key={food.instance_id || food.food_id || idx}
                  className={`food-item-card glass-panel ${isSelected ? 'food-card-focused' : ''}`}
                  id={`food-card-${food.food_id || food.instance_id}`}
                  onClick={() => setSelectedFoodId(food.instance_id || food.food_id)}
                >
                  <div className="food-card-header">
                    <div className="food-names">
                      <h4 className="food-name-standardized">
                        {food.standardized_name}{' '}
                        {food.count > 1 && <span className="count-badge-pill">×{food.count}</span>}
                      </h4>
                      <span className="food-name-detected">Detected as: "{food.detected_name}"</span>
                    </div>
                    <div className="food-badges">
                      <span className="category-pill">{food.category}</span>
                      <span className={`confidence-pill ${food.retrieval_confidence}`}>
                        Match: {food.retrieval_confidence.toUpperCase()} ({Math.round(food.retrieval_score * 100)}%)
                      </span>
                    </div>
                  </div>

                  <div className="food-card-body">
                    {/* Portion editor */}
                    <div className="portion-editor-area">
                      <label className="input-label" htmlFor={`portion-input-${food.food_id || idx}`}>
                        Portion (grams):
                      </label>
                      <div className="portion-input-row">
                        <input
                          type="number"
                          id={`portion-input-${food.food_id || idx}`}
                          min="10"
                          max="2000"
                          step="5"
                          value={editedPortions[food.food_id] ?? food.portion.estimated_grams}
                          onChange={(e) => handlePortionChange(food.food_id, e.target.value)}
                          className="portion-number-input"
                        />
                        <span className="grams-unit">g</span>
                      </div>

                      <div className="portion-multipliers">
                        <button
                          type="button"
                          className="btn-multiplier"
                          onClick={() => applyPortionPreset(food.food_id, 0.7)}
                        >
                          Small (0.7x)
                        </button>
                        <button
                          type="button"
                          className="btn-multiplier"
                          onClick={() => applyPortionPreset(food.food_id, 1.0)}
                        >
                          Regular (1.0x)
                        </button>
                        <button
                          type="button"
                          className="btn-multiplier"
                          onClick={() => applyPortionPreset(food.food_id, 1.5)}
                        >
                          Large (1.5x)
                        </button>
                      </div>
                    </div>

                    {/* Calculated Nutrition Matrix */}
                    <div className="food-nutrition-metrics">
                      <div className="metric-box calorie-metric">
                        <span className="metric-num">{Math.round(food.nutrition.calories_kcal)}</span>
                        <span className="metric-tag">kcal</span>
                      </div>
                      <div className="metric-box">
                        <span className="metric-num">{food.nutrition.protein_g.toFixed(1)}g</span>
                        <span className="metric-tag">Protein</span>
                      </div>
                      <div className="metric-box">
                        <span className="metric-num">{food.nutrition.carbs_g.toFixed(1)}g</span>
                        <span className="metric-tag">Carbs</span>
                      </div>
                      <div className="metric-box">
                        <span className="metric-num">{food.nutrition.fat_g.toFixed(1)}g</span>
                        <span className="metric-tag">Fat</span>
                      </div>
                      {food.nutrition.fiber_g !== null && (
                        <div className="metric-box">
                          <span className="metric-num">{food.nutrition.fiber_g.toFixed(1)}g</span>
                          <span className="metric-tag">Fiber</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="food-card-footer">
                    <span className="data-source-note">Source: {food.source}</span>
                    <span className="portion-method-note">Portion: {food.portion.method}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Visual Debug Panel */}
          {showDebug && (
            <div className="visual-debug-panel animate-fade-in" id="visual-debug-panel">
              <h3>🔍 Multi-Stage Pipeline Diagnostic Trace</h3>

              <div className="debug-step-card">
                <div className="debug-step-title">
                  <span>Step 1: Input Validation & Image Resolution</span>
                  <span className="category-pill">VALIDATED</span>
                </div>
                <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                  Dimensions: {analysisResult.image?.width || 800} × {analysisResult.image?.height || 600} px •
                  Vision Mode: <strong>{analysisResult.vision_mode}</strong> • Candidate Regions:{' '}
                  {analysisResult.debug?.candidate_regions_count || analysisResult.foods.length}
                </p>
              </div>

              <div className="debug-step-card">
                <div className="debug-step-title">
                  <span>Step 2 & 3: Candidate Region Proposals & Classification</span>
                  <span className="category-pill">LOCALIZED</span>
                </div>
                <div>
                  {analysisResult.foods.map((f, i) => (
                    <div key={i} style={{ marginBottom: '8px', fontSize: '13px' }}>
                      <span className="debug-candidate-badge">Region #{i + 1}</span>
                      <strong>{f.detected_name}</strong> (Visual Conf:{' '}
                      {Math.round(f.recognition_confidence * 100)}%, Count: {f.count})
                      {f.detection?.bbox && (
                        <span style={{ color: 'var(--text-muted)', marginLeft: '8px' }}>
                          bbox: [{f.detection.bbox.ymin}, {f.detection.bbox.xmin}, {f.detection.bbox.ymax},{' '}
                          {f.detection.bbox.xmax}]
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div className="debug-step-card">
                <div className="debug-step-title">
                  <span>Step 4: Strict Anti-False-Positive Matching & Category Safeguards</span>
                  <span className="category-pill">VERIFIED</span>
                </div>
                <div>
                  {analysisResult.debug?.retrieval_details?.map((item, idx) => (
                    <div key={idx} style={{ marginBottom: '12px', fontSize: '13px' }}>
                      <strong>Query: "{item.query}"</strong> → Status:{' '}
                      <span style={{ color: 'var(--saffron-400)' }}>{item.status}</span>
                      <div style={{ marginTop: '4px' }}>
                        <span style={{ color: 'var(--text-muted)' }}>Top Matches: </span>
                        {item.top_candidates?.map((c, ci) => (
                          <span key={ci} className="debug-candidate-badge">
                            {c.name || c.food} ({c.similarity_score ?? c.score})
                          </span>
                        ))}
                        {item.rejected_candidates?.length > 0 && (
                          <div style={{ marginTop: '4px' }}>
                            <span style={{ color: '#fca5a5' }}>Rejected False Positives: </span>
                            {item.rejected_candidates.map((rc, rci) => (
                              <span key={rci} className="debug-candidate-badge rejected">
                                ✕ {rc.food} ({rc.reason})
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="debug-step-card">
                <div className="debug-step-title">
                  <span>Step 5 & 6: Deterministic Calculation Formula</span>
                  <span className="category-pill">ATWATER 4-4-9</span>
                </div>
                <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                  For each food item: Energy (kcal) = (Protein × 4) + (Carbohydrates × 4) + (Fat × 9).
                  Total Meal = $\sum(\text{portions})$. The AI model never generates calorie numbers directly.
                </p>
              </div>
            </div>
          )}

          {/* Academic & Medical Disclaimer Card */}
          <div className="academic-disclaimer-card" id="academic-disclaimer-card">
            <div className="disclaimer-icon">⚠️</div>
            <div className="disclaimer-content">
              <h4>Academic Research & Informational Prototype</h4>
              <p>{analysisResult.disclaimer}</p>
              <p className="disclaimer-sub">
                DietAI24 demonstrates how grounding vision outputs into indexed food composition databases
                prevents hallucination in health applications. Not intended for clinical or medical decision making.
              </p>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
