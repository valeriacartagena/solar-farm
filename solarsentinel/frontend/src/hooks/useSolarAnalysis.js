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
  const [isDroneAnalyzing, setIsDroneAnalyzing] = useState(false);
  const [droneAnalysisSource, setDroneAnalysisSource] = useState(null);
  const [pipelineResults, setPipelineResults] = useState([]);
  const [activeFaultIndex, setActiveFaultIndex] = useState(0);
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);

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

  // ── Drone video analysis (single-stage Overshoot) ─────────────────────────
  const runDroneAnalysis = async () => {
    if (!uploadedFile) {
      alert("Please upload a video file first.");
      return;
    }

    setIsDroneAnalyzing(true);
    setIsLoading(true);

    try {
      let currentSessionId = sessionId;
      if (!currentSessionId) {
        setActiveStep("uploading");
        const formData = new FormData();
        formData.append("file", uploadedFile);
        const uploadRes = await fetch(`${API_BASE}/upload`, {
          method: 'POST',
          body: formData,
        });
        const uploadData = await uploadRes.json();
        currentSessionId = uploadData.session_id;
        setSessionId(currentSessionId);
      }

      setActiveStep("drone_analyzing");
      const analyzeRes = await fetch(`${API_BASE}/drone-analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: currentSessionId })
      });
      const analyzeData = await analyzeRes.json();

      if (analyzeData.error) {
        alert(`Drone analysis error: ${analyzeData.error}`);
        return;
      }

      setDetections(analyzeData.detections);
      setDroneAnalysisSource("overshoot_ai");

      const counts = {};
      let cost = 0;
      for (const d of analyzeData.detections) {
        counts[d.fault_type] = (counts[d.fault_type] || 0) + 1;
        cost += d.cost_estimate;
      }
      setFaultCounts(counts);
      setTotalCost(cost);
      setReportText(
        `Drone Video Analysis Complete (via Overshoot AI)\n\n` +
        `Overall Condition: ${analyzeData.overall_condition}\n` +
        `Clips Analyzed: ${analyzeData.clips_analyzed}\n` +
        `Total Faults Detected: ${analyzeData.detections.length}\n` +
        `Estimated Total Cost: $${cost.toLocaleString()}`
      );

    } catch (error) {
      console.error("Drone analysis failed:", error);
      alert("Drone analysis failed. See console for details.");
    } finally {
      setIsLoading(false);
      setIsDroneAnalyzing(false);
      setActiveStep(null);
    }
  };

  // ── Two-stage pipeline (Overshoot + YOLOv8) ──────────────────────────────
  const runTwoStagePipeline = async () => {
    if (!uploadedFile) {
      alert("Please upload a video file first.");
      return;
    }

    setIsPipelineRunning(true);
    setIsLoading(true);
    setPipelineResults([]);
    setActiveFaultIndex(0);

    try {
      let currentSessionId = sessionId;
      if (!currentSessionId) {
        setActiveStep("uploading");
        const formData = new FormData();
        formData.append("file", uploadedFile);
        const uploadRes = await fetch(`${API_BASE}/upload`, {
          method: 'POST',
          body: formData,
        });
        const uploadData = await uploadRes.json();
        currentSessionId = uploadData.session_id;
        setSessionId(currentSessionId);
      }

      setActiveStep("pipeline_running");
      const pipelineRes = await fetch(`${API_BASE}/drone-pipeline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: currentSessionId })
      });
      const pipelineData = await pipelineRes.json();

      if (pipelineData.error) {
        alert(`Pipeline error: ${pipelineData.error}`);
        return;
      }

      setPipelineResults(pipelineData.pipeline_results);

      const mappedDetections = pipelineData.pipeline_results.map((r, i) => {
        const yoloDet = r.yolo_detections[0];
        return {
          panel_id: r.fault_id,
          fault_type: yoloDet ? yoloDet.class_name : r.overshoot_fault.fault_type,
          confidence: yoloDet ? yoloDet.confidence : r.overshoot_fault.confidence,
          severity: r.overshoot_fault.severity === "high" ? "critical" : r.overshoot_fault.severity === "medium" ? "moderate" : "minor",
          lat: 35.6 + (Math.random() - 0.5) * 0.004,
          lng: 139.7 + (Math.random() - 0.5) * 0.004,
          cost_estimate: r.overshoot_fault.severity === "high" ? 1000 : r.overshoot_fault.severity === "medium" ? 500 : 100,
          description: r.overshoot_fault.description,
        };
      });
      setDetections(mappedDetections);

      const counts = {};
      let cost = 0;
      for (const d of mappedDetections) {
        counts[d.fault_type] = (counts[d.fault_type] || 0) + 1;
        cost += d.cost_estimate;
      }
      setFaultCounts(counts);
      setTotalCost(cost);
      setReportText(
        `Two-Stage Pipeline Analysis Complete\n\n` +
        `Stage 1 (Overshoot AI): ${pipelineData.frames_analyzed} frames scanned\n` +
        `Stage 2 (YOLOv8): ${pipelineData.total_faults} fault regions classified\n` +
        `Total Faults: ${pipelineData.total_faults}\n` +
        `Estimated Total Cost: $${cost.toLocaleString()}`
      );

    } catch (error) {
      console.error("Pipeline failed:", error);
      alert("Pipeline failed. See console for details.");
    } finally {
      setIsLoading(false);
      setIsPipelineRunning(false);
      setActiveStep(null);
    }
  };

  // ── Farm lookup on coordinate blur ────────────────────────────────────────
  const lookupFarm = async () => {
    const { lat, lng } = parsedCoords();
    if (lat === 35.6 && lng === 139.7) return;
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
    isLoading, activeStep, isDroneAnalyzing, droneAnalysisSource,
    pipelineResults, activeFaultIndex, setActiveFaultIndex, isPipelineRunning,
    handleFileUpload, handleDrop, runAnalysis, runDroneAnalysis, runTwoStagePipeline,
    generateSynthetic, lookupFarm, parsedCoords,
  };
}
