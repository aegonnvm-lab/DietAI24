import React, { useState, useEffect } from 'react';
import { getFoods } from '../services/api';

const QUICK_FILTERS = [
  'All',
  'Eggs & Poultry',
  'Dals & Lentils',
  'Rice Dishes',
  'Breads',
  'Curries',
  'Fast Food',
  'Dairy',
  'Snacks',
  'Beverages',
  'Produce',
];

export default function FoodDatabase() {
  const [foods, setFoods] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState('All');
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchFoodList();
  }, [activeFilter]);

  const fetchFoodList = async (searchQuery = search) => {
    setLoading(true);
    setError(null);
    try {
      const categoryParam = activeFilter === 'All' ? null : activeFilter;
      const data = await getFoods({
        search: searchQuery,
        category: categoryParam,
        limit: 150,
      });
      setFoods(data.foods || []);
      if (data.categories && data.categories.length > 0) {
        setCategories(data.categories);
      }
    } catch (err) {
      setError(err.message || 'Failed to load foods');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchChange = (e) => {
    const val = e.target.value;
    setSearch(val);
    fetchFoodList(val);
  };

  return (
    <div className="food-database-container" id="food-database-container">
      <div className="database-header">
        <h2>Global & Indian Nutrition Knowledge Base</h2>
        <p>
          Standardized nutritional reference records curated from <strong>IFCT 2017</strong> (Indian Food
          Composition Tables) and <strong>USDA FoodData Central</strong>. Every record is verified for Atwater physical
          consistency and indexed for semantic vector retrieval.
        </p>
      </div>

      {/* Search & Filter Bar */}
      <div className="database-controls-card glass-panel" id="database-controls">
        <div className="search-input-wrapper">
          <svg className="search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input
            type="text"
            id="food-search-input"
            placeholder="Search by name, alias, cuisine, or ingredient (e.g. omelette, paneer, dal, burger)..."
            value={search}
            onChange={handleSearchChange}
          />
          {search && (
            <button className="clear-search-btn" onClick={() => { setSearch(''); fetchFoodList(''); }}>✕</button>
          )}
        </div>

        {/* Category & Cuisine Filters */}
        <div className="category-pills-row" id="category-pills">
          {QUICK_FILTERS.map((cat) => (
            <button
              key={cat}
              id={`filter-cat-${cat.toLowerCase().replace(/[^a-z0-9]/g, '-')}`}
              className={`category-filter-btn ${activeFilter === cat ? 'active' : ''}`}
              onClick={() => setActiveFilter(cat)}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Database Record Counter */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
          Showing <strong>{foods.length}</strong> verified nutrition records
        </span>
        <span style={{ fontSize: '12px', color: 'var(--saffron-400)', background: 'rgba(245, 158, 11, 0.1)', padding: '4px 10px', borderRadius: '12px' }}>
          ✓ Verified Ingestion Architecture
        </span>
      </div>

      {/* Grid of Foods */}
      {loading ? (
        <div className="loading-state-box">
          <div className="spinner"></div>
          <span>Loading verified nutrition records...</span>
        </div>
      ) : error ? (
        <div className="error-banner">
          Failed to load database: {error}
        </div>
      ) : foods.length === 0 ? (
        <div className="empty-state-box">
          <span>🔍 No matching food records found for "{search}". Try searching for omelette, dosa, dal, or paneer.</span>
        </div>
      ) : (
        <div className="foods-database-grid" id="foods-grid">
          {foods.map((food) => (
            <div key={food.food_id} className="db-food-card glass-panel" id={`db-card-${food.food_id}`}>
              <div className="db-card-header">
                <span className="db-food-id">{food.food_id}</span>
                <span className="db-category-tag">{food.category}</span>
              </div>

              <h3 className="db-food-title">{food.food_name}</h3>

              {food.aliases && food.aliases.length > 0 && (
                <div className="db-aliases-row">
                  <span className="alias-label">Aliases:</span>
                  <span className="alias-text">{food.aliases.slice(0, 4).join(', ')}</span>
                </div>
              )}

              {/* Per 100g Nutrition Metrics */}
              <div className="db-nutrition-row">
                <div className="db-metric-item highlight">
                  <span className="num">{Math.round(food.nutrition?.calories_100g || food.calories_100g || 0)}</span>
                  <span className="label">kcal/100g</span>
                </div>
                <div className="db-metric-item">
                  <span className="num">{(food.nutrition?.protein_100g || food.protein_100g || 0).toFixed(1)}g</span>
                  <span className="label">Protein</span>
                </div>
                <div className="db-metric-item">
                  <span className="num">{(food.nutrition?.carbs_100g || food.carbs_100g || 0).toFixed(1)}g</span>
                  <span className="label">Carbs</span>
                </div>
                <div className="db-metric-item">
                  <span className="num">{(food.nutrition?.fat_100g || food.fat_100g || 0).toFixed(1)}g</span>
                  <span className="label">Fat</span>
                </div>
              </div>

              <div className="db-card-footer">
                <span className="db-portion-hint">
                  Default Serving: ~{food.default_portion_g}g
                </span>
                <span className="db-source-tag">{food.source}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
