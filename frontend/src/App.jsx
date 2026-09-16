import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import MealAnalysis from './components/MealAnalysis';
import FoodDatabase from './components/FoodDatabase';
import Methodology from './components/Methodology';
import { getHealthStatus } from './services/api';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('analyze');
  const [healthData, setHealthData] = useState(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkHealth = async () => {
    try {
      const data = await getHealthStatus();
      setHealthData(data);
      setIsConnected(true);
    } catch {
      setIsConnected(false);
    }
  };

  return (
    <div className="app-layout" id="app-root-layout">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        healthData={healthData}
        isConnected={isConnected}
      />

      <main className="main-content-area" id="main-content-area">
        {activeTab === 'analyze' && <MealAnalysis />}
        {activeTab === 'database' && <FoodDatabase />}
        {activeTab === 'methodology' && <Methodology />}
      </main>

      <footer className="site-footer" id="site-footer">
        <div className="footer-content">
          <div className="footer-left">
            <span className="footer-logo">🍛 DietAI24</span>
            <span className="footer-desc">
              Academic Indian Food Calorie Estimation Framework • Milestone 1
            </span>
          </div>
          <div className="footer-right">
            <span className="footer-disclaimer">
              Educational prototype. Grounded in verified Indian food composition data.
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
