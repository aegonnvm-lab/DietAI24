import React from 'react';

export default function Header({ activeTab, setActiveTab, healthData, isConnected }) {
  return (
    <header className="site-header" id="site-header">
      <div className="header-container">
        {/* Brand Logo & Title */}
        <div className="brand-wrapper" id="brand-wrapper" onClick={() => setActiveTab('analyze')}>
          <div className="brand-icon-box">
            <span className="brand-emoji">🍛</span>
          </div>
          <div className="brand-text">
            <div className="brand-title-row">
              <span className="brand-title">DietAI24</span>
              <span className="research-badge" id="research-badge">Milestone 1</span>
            </div>
            <span className="brand-subtitle">Indian Food Calorie & Nutrition Estimator</span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="nav-tabs" id="main-navigation">
          <button
            id="nav-btn-analyze"
            className={`nav-tab-btn ${activeTab === 'analyze' ? 'active' : ''}`}
            onClick={() => setActiveTab('analyze')}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
              <circle cx="12" cy="13" r="4"></circle>
            </svg>
            <span>Analyze Meal</span>
          </button>

          <button
            id="nav-btn-database"
            className={`nav-tab-btn ${activeTab === 'database' ? 'active' : ''}`}
            onClick={() => setActiveTab('database')}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
            </svg>
            <span>Food Database</span>
          </button>

          <button
            id="nav-btn-methodology"
            className={`nav-tab-btn ${activeTab === 'methodology' ? 'active' : ''}`}
            onClick={() => setActiveTab('methodology')}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
              <polyline points="2 17 12 22 22 17"></polyline>
              <polyline points="2 12 12 17 22 12"></polyline>
            </svg>
            <span>Architecture & RAG</span>
          </button>
        </nav>

        {/* System Status Indicators */}
        <div className="header-status-area" id="header-status-area">
          {/* Health Status Pill */}
          <div className="status-pill" id="backend-status-pill" title="FastAPI Backend Health">
            <span className={`status-dot ${isConnected ? 'online' : 'offline'}`}></span>
            <span className="status-text">
              {isConnected ? 'API Online' : 'Connecting...'}
            </span>
          </div>

          {/* Model Mode Badge */}
          <div className="vision-mode-tag" id="vision-mode-tag" title="Active Vision Processing Mode">
            <span className="mode-indicator">Mode:</span>
            <span className="mode-value">
              {healthData?.vision_mode === 'claude' ? 'Claude 3.5' : 'Mock (Local)'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
