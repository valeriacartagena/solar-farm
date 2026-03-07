import { useState, useRef } from 'react';

const API_BASE = 'http://localhost:8000/api';

export function useSolarAnalysis() {
  const [sessionId, setSessionId]           = useState(null);
  const [uploadedFile, setUploadedFile]     = useState(null);
  const [videoUrl, setVideoUrl]             = useState(null);
  const [coordinates, setCoordinates]       = useState('');
  const [farmArea, setFarmArea]             = useState('');
  const [moduleType, setModuleType]         = useState('crystalline silicon');
  const [axisType, setAxisType]             = useState('Fixed');
  const [capacityMW, setCapacityMW]         = useState(1.0);

  const [faultTypes, setFaultTypes] = useState([
    'hotspot', 'cracked cell', 'dust accumulation'
  ]);
  const [geeDatasets, setGeeDatasets] = useState([
    'COPERNICUS/S2_SR_HARMONIZED',
    'LANDSAT/LC09/C02/T1_L2',
    'NASA/HLS/HLSL30/v002',
  ]);

  const [detections, setDetections]           = useState([]);
  const [annotatedFrames, setAnnotatedFrames] = useState([]);
  const [geeData, setGeeData]                 = useState(null);
  const [reportText, setReportText]           = useState('');
  const [faultCounts, setFaultCounts]         = useState({});
  const [totalCost, setTotalCost]             = useState(0);

  const [isLoading, setIsLoading]   = useState(false);
  const [activeStep, setActiveStep] = useState(null);

  // ── File handling ─────────────────────────────────────────────────────────
  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) { setUploadedFile(file); setVideoUrl(URL.createObjectURL(file)); }
  };
  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) { setUploadedFile(file); setVideoUrl(URL.createObjectURL(file)); }
  };

  // ── Parse lat/lng from the coordinates string ─────────────────────────────
  const parsedCoords = () => {
    const parts = coordinates.split(',').map(s => parseFloat(s.trim()));
    if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
      return { lat: parts[0], lng: parts[1] };
    }
    return { lat: 35.6, lng: 139.7 }; // default fallback
  };

  // ── Main analysis flow ────────────────────────────────────────────────────
  const runAnalysis = async () => {
    if (!uploadedFile) { alert('Please upload a file first.'); return; }

    setIsLoading(true);
    try {
      // Step 1: Upload
      setActiveStep('uploading');
      const formData = new FormData();
      formData.append('file', uploadedFile);
      const uploadRes  = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData });
      const uploadData = await uploadRes.json();
      const sid        = uploadData.session_id;
      setSessionId(sid);

      // Step 2: CV Detection
      setActiveStep('detecting');
      const detectRes  = await fetch(`${API_BASE}/detect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sid, fault_types: faultTypes }),
      });
      const detectData = await detectRes.json();
      // Preliminary detections (before satellite enrichment)
      setDetections(detectData.detections || []);
      setAnnotatedFrames(detectData.annotated_frame_urls || []);

      // Step 3: GEE — pass CV detections in for satellite enrichment
      setActiveStep('fetching_gee');
      const { lat, lng } = parsedCoords();
      const geeRes  = await fetch(`${API_BASE}/gee`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat,
          lng,
          area_sq_ft:      farmArea ? parseFloat(farmArea) : null,
          module_type:     moduleType,
          axis_type:       axisType,
          capacity_dc_mw:  capacityMW,
          dataset_ids:     geeDatasets,
          detections:      detectData.detections || [],   // ← pass CV faults in
        }),
      });
      const geeResult = await geeRes.json();
      setGeeData(geeResult);

      // Use enriched detections (carry satellite context) for map pins
      if (geeResult.enriched_detections?.length) {
        setDetections(geeResult.enriched_detections);
      }

      // Step 4: AI Report
      setActiveStep('generating_report');
      const analysisRes  = await fetch(`${API_BASE}/analysis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          detections: geeResult.enriched_detections || detectData.detections || [],
          gee_data:   geeResult,
          fault_types: faultTypes,
        }),
      });
      const analysisData = await analysisRes.json();
      setReportText(analysisData.report_text || '');
      setFaultCounts(analysisData.fault_counts || {});
      setTotalCost(analysisData.total_cost || 0);

    } catch (error) {
      console.error('Analysis failed:', error);
      alert('Analysis failed — check the console for details.');
    } finally {
      setIsLoading(false);
      setActiveStep(null);
    }
  };

  // ── Farm lookup on coordinate blur ────────────────────────────────────────
  const lookupFarm = async () => {
    const { lat, lng } = parsedCoords();
    if (lat === 35.6 && lng === 139.7) return; // haven't entered coords yet
    try {
      const res  = await fetch(`${API_BASE}/farm-lookup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat, lng, radius_km: 10 }),
      });
      const data = await res.json();
      if (data.found) {
        if (data.module_type && data.module_type !== 'unknown') {
          setModuleType(data.module_type.toLowerCase());
        }
        if (data.capacity_dc_mw) setCapacityMW(data.capacity_dc_mw);
      }
      return data;
    } catch (e) {
      console.warn('Farm lookup failed:', e);
    }
  };

  // ── Synthetic generation ──────────────────────────────────────────────────
  const generateSynthetic = (generator, faultType) =>
    fetch(`${API_BASE}/synthetic`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ generator, fault_type: faultType, count: 1 }),
    });

  return {
    sessionId, uploadedFile, videoUrl,
    coordinates, setCoordinates,
    farmArea, setFarmArea,
    moduleType, setModuleType,
    axisType, setAxisType,
    capacityMW, setCapacityMW,
    faultTypes, setFaultTypes,
    geeDatasets, setGeeDatasets,
    detections, annotatedFrames, geeData,
    reportText, faultCounts, totalCost,
    isLoading, activeStep,
    handleFileUpload, handleDrop, runAnalysis, generateSynthetic, lookupFarm,
    parsedCoords,
  };
}
