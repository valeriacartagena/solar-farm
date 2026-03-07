import React, { useState } from 'react';

export function Sidebar({ state }) {
  const [toast, setToast] = useState(null);
  const [coordinates, setCoordinates] = useState('');
  const [farmArea, setFarmArea] = useState('');

  const {
    uploadedFile, faultTypes, setFaultTypes,
    geeDatasets, setGeeDatasets, isLoading, activeStep,
    handleFileUpload, handleDrop, runAnalysis, generateSynthetic
  } = state;

  const updateEntry = (arr, i, val, setter) => {
    const next = [...arr]; next[i] = val; setter(next);
  };

  const handleSynthetic = async (name) => {
    setToast({ name, state: 'loading' });
    try {
      await generateSynthetic(name, faultTypes[0]);
      setToast({ name, state: 'done' });
      setTimeout(() => setToast(null), 3000);
    } catch { setToast(null); }
  };

  return (
    <div className="sidebar">
      {/* Upload */}
      <div className="sidebar-section">
        <div className="sidebar-label">Upload Feed</div>
        <div
          className="upload-zone"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
        >
          <input type="file" onChange={handleFileUpload} accept=".mp4,.mov,.jpg,.png,.tiff" />
          <div className="upload-icon">
            <svg fill="none" stroke="white" strokeWidth="2.5" viewBox="0 0 24 24">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" />
            </svg>
          </div>
          {uploadedFile ? (
            <span className="upload-filename">{uploadedFile.name}</span>
          ) : (
            <>
              <span className="upload-text"><strong>Choose a file</strong> or drag it here</span>
              <span className="upload-hint">MP4 · MOV · JPG · PNG · TIFF</span>
            </>
          )}
        </div>
      </div>

      {/* Farm Location */}
      <div className="sidebar-section">
        <div className="sidebar-label">Solar Farm Location</div>
        <div className="field-group">
          <input
            className="dark-input"
            value={coordinates}
            onChange={(e) => setCoordinates(e.target.value)}
            placeholder="Coordinates (lat, lng)"
          />
          <input
            className="dark-input"
            value={farmArea}
            onChange={(e) => setFarmArea(e.target.value)}
            placeholder="Area of solar farm (sq ft)"
          />
        </div>
      </div>

      {/* Fault Types */}
      <div className="sidebar-section">
        <div className="sidebar-label">CV Analysis Properties</div>
        <div className="field-group">
          {faultTypes.map((ft, i) => (
            <input
              key={i} className="dark-input"
              value={ft}
              onChange={(e) => updateEntry(faultTypes, i, e.target.value, setFaultTypes)}
              placeholder={`Fault type ${i + 1}`}
            />
          ))}
        </div>
      </div>

      {/* GEE Datasets */}
      <div className="sidebar-section">
        <div className="sidebar-label">Satellite Datasets</div>
        <div className="field-group">
          {geeDatasets.map((ds, i) => (
            <input
              key={i} className="dark-input"
              value={ds}
              onChange={(e) => updateEntry(geeDatasets, i, e.target.value, setGeeDatasets)}
              placeholder={`Dataset ${i + 1}`}
            />
          ))}
        </div>
      </div>

      {/* Synthetic Gen */}
      <div className="sidebar-section" style={{ marginBottom: 'auto' }}>
        <div className="sidebar-label">Synthetic Data Generators</div>
        <div className="pill-group">
          {['Gemini Veo', 'Nano Banana 2', 'Overshoot.ai'].map(gen => (
            <button key={gen} className="pill-btn" onClick={() => handleSynthetic(gen)}>
              <span>{gen}</span>
              {toast?.name === gen && toast?.state === 'loading' && <span className="spinner" />}
              {toast?.name === gen && toast?.state === 'done'
                ? <span style={{ color: '#22c55e', fontSize: 16 }}>✓</span>
                : <span className="pill-dot" />
              }
            </button>
          ))}
        </div>
        {toast?.state === 'done' && (
          <p className="toast-msg" style={{ marginTop: 10 }}>✨ Synthetic images generated</p>
        )}
      </div>

      {/* Status / Run */}
      <div className="sidebar-section" style={{ marginBottom: 0 }}>
        {isLoading && (
          <p className="step-label">
            {activeStep === 'uploading' && '⏳ Extracting frames...'}
            {activeStep === 'detecting' && '🔍 Running CV detection...'}
            {activeStep === 'fetching_gee' && '🛰️ Pulling satellite data...'}
            {activeStep === 'generating_report' && '🧠 Generating AI report...'}
          </p>
        )}
        <button
          className="run-btn"
          onClick={runAnalysis}
          disabled={isLoading || !uploadedFile}
          style={{ marginTop: 12, color: '#ffffff' }}
        >
          {isLoading ? 'Analyzing...' : 'Run Analysis'}
        </button>
      </div>
    </div>
  );
}
