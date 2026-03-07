import React, { useState } from 'react';

export function Sidebar({ state }) {
  const [toast, setToast] = useState(null);

  const {
    uploadedFile, faultTypes, setFaultTypes,
    geeDatasets, setGeeDatasets, isLoading, activeStep, isDroneAnalyzing, isPipelineRunning,
    handleFileUpload, handleDrop, runAnalysis, runDroneAnalysis, runTwoStagePipeline, generateSynthetic
  } = state;

  const updateArrayEntry = (arr, index, val, setter) => {
    const newArr = [...arr];
    newArr[index] = val;
    setter(newArr);
  };

  const handleSynthetic = async (name) => {
    setToast({ name, state: 'loading' });
    try {
      await generateSynthetic(name, faultTypes[0]);
      setToast({ name, state: 'done' });
      setTimeout(() => setToast(null), 3000);
    } catch {
      setToast(null);
    }
  };

  return (
    <div className="sidebar">
      {/* Upload Zone */}
      <div
        className="upload-zone"
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        <input type="file" onChange={handleFileUpload} accept=".mp4,.mov,.jpg,.png,.tiff" />
        <svg width="32" height="32" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" />
        </svg>
        <span style={{ marginTop: 6 }}>
          {uploadedFile ? uploadedFile.name : 'Choose a file or drag it here.'}
        </span>
      </div>

      {/* Fault Types */}
      <h3>Desired properties to analyze via CV</h3>
      <div className="field-group">
        {faultTypes.map((ft, i) => (
          <input
            key={i} className="dark-input"
            value={ft}
            onChange={(e) => updateArrayEntry(faultTypes, i, e.target.value, setFaultTypes)}
            placeholder={`fault type #${i + 1}`}
          />
        ))}
      </div>

      {/* GEE Datasets */}
      <h3>Satellite Datasets used</h3>
      <div className="field-group">
        {geeDatasets.map((ds, i) => (
          <input
            key={i} className="dark-input"
            value={ds}
            onChange={(e) => updateArrayEntry(geeDatasets, i, e.target.value, setGeeDatasets)}
            placeholder={`GEE satellite # ${i + 1} hyperlink`}
          />
        ))}
      </div>

      {/* Synthetic Gen */}
      <h3>Synthetic data generation</h3>
      <div className="pill-group">
        {['Gemini Veo', 'Nano Banana 2', 'Overshoot.ai'].map(gen => (
          <button key={gen} className="pill-btn" onClick={() => handleSynthetic(gen)}>
            <span>{gen}</span>
            {toast?.name === gen && toast?.state === 'loading' && <span className="spinner" />}
            {toast?.name === gen && toast?.state === 'done' && (
              <span style={{ color: '#22c55e', fontSize: 18 }}>✓</span>
            )}
          </button>
        ))}
      </div>

      {toast?.state === 'done' && (
        <p className="toast-msg">✨ Synthetic images generated</p>
      )}

      {isLoading && (
        <p className="step-label">
          {activeStep === 'uploading' && '⏳ Extracting frames...'}
          {activeStep === 'detecting' && '🔍 Running CV detection...'}
          {activeStep === 'fetching_gee' && '🛰️ Pulling satellite data...'}
          {activeStep === 'generating_report' && '🧠 Generating report...'}
          {activeStep === 'drone_analyzing' && '🎥 Analyzing drone video with AI Vision...'}
          {activeStep === 'pipeline_running' && '🔬 Stage 1: AI Vision scanning → Stage 2: YOLOv8 classifying...'}
        </p>
      )}

      <button
        className="run-btn"
        onClick={runAnalysis}
        disabled={isLoading || !uploadedFile}
      >
        {isLoading && !isDroneAnalyzing && !isPipelineRunning ? 'Analyzing...' : 'Run Analysis'}
      </button>

      <button
        className="run-btn"
        onClick={runDroneAnalysis}
        disabled={isLoading || !uploadedFile}
        style={{ marginTop: 8, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}
      >
        {isDroneAnalyzing ? 'Analyzing Video...' : 'Drone Video Analysis (Overshoot AI)'}
      </button>

      <button
        className="run-btn"
        onClick={runTwoStagePipeline}
        disabled={isLoading || !uploadedFile}
        style={{ marginTop: 8, background: 'linear-gradient(135deg, #f97316, #ef4444)' }}
      >
        {isPipelineRunning ? 'Pipeline Running...' : 'Two-Stage Pipeline (Overshoot + YOLOv8)'}
      </button>
    </div>
  );
}
