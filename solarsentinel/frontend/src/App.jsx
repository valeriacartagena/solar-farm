import React from 'react';
import { Sidebar } from './components/Sidebar';
import { DroneVideoPlayer } from './components/DroneVideoPlayer';
import { LiveMap } from './components/LiveMap';
import { AnalysisPanel } from './components/AnalysisPanel';
import { useSolarAnalysis } from './hooks/useSolarAnalysis';

function App() {
  const state = useSolarAnalysis();

  return (
    <>
      {/* Top Navigation Bar */}
      <nav className="top-nav">
        <div className="nav-logo">
          <span className="nav-logo-text">Radiant</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 13, color: 'rgba(255,255,255,0.45)' }}>
          <span>Fault Detection</span>
          <span style={{ opacity: 0.3 }}>·</span>
          <span>Satellite Analysis</span>
          <span style={{ opacity: 0.3 }}>·</span>
          <span>AI Reports</span>
        </div>

        <div className="demo-badge">Demo Mode</div>
      </nav>

      {/* Main Dashboard */}
      <div className="app">
        <Sidebar state={state} />
        <div className="center-col">
          <DroneVideoPlayer state={state} />
          <LiveMap state={state} />
        </div>
        <AnalysisPanel state={state} />
      </div>
    </>
  );
}

export default App;
