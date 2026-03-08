import React from 'react';
import { Sidebar } from './components/Sidebar';
import { DroneVideoPlayer } from './components/DroneVideoPlayer';
import { LiveMap } from './components/LiveMap';
import { AnalysisPanel } from './components/AnalysisPanel';
import { useSolarAnalysis } from './hooks/useSolarAnalysis';

function App() {
  const state = useSolarAnalysis();

  return (
    <div className="app">
      <Sidebar state={state} />
      <div className="center-col">
        <DroneVideoPlayer state={state} />
        <LiveMap state={state} />
      </div>
      <AnalysisPanel state={state} />
      <div className="demo-badge">Demo Mode</div>
    </div>
  );
}

export default App;
