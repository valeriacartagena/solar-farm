import { useState } from 'react';

const API_BASE = 'http://localhost:8000/api';

export function useSolarAnalysis() {
  const [sessionId, setSessionId] = useState(null);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [videoUrl, setVideoUrl] = useState(null);
  
  const [faultTypes, setFaultTypes] = useState([
    "hotspot", "cracked cell", "dust accumulation"
  ]);
  
  const [geeDatasets, setGeeDatasets] = useState([
    "COPERNICUS/S2_SR_HARMONIZED",
    "LANDSAT/LC09/C02/T1_L2",
    "NASA/HLS/HLSL30/v002"
  ]);
  
  const [detections, setDetections] = useState([]);
  const [annotatedFrames, setAnnotatedFrames] = useState([]);
  const [geeData, setGeeData] = useState(null);
  const [reportText, setReportText] = useState("");
  const [faultCounts, setFaultCounts] = useState({});
  const [totalCost, setTotalCost] = useState(0);
  
  const [isLoading, setIsLoading] = useState(false);
  const [activeStep, setActiveStep] = useState(null); // 'uploading' | 'detecting' | 'fetching_gee' | 'generating_report'

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setUploadedFile(file);
      const url = URL.createObjectURL(file);
      setVideoUrl(url);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) {
      setUploadedFile(file);
      const url = URL.createObjectURL(file);
      setVideoUrl(url);
    }
  };

  const runAnalysis = async () => {
    if (!uploadedFile) {
        alert("Please upload a file first.");
        return;
    }
    
    setIsLoading(true);
    
    try {
      // Step 1: Upload
      setActiveStep("uploading");
      const formData = new FormData();
      formData.append("file", uploadedFile);
      
      const uploadRes = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      });
      const uploadData = await uploadRes.json();
      const currentSessionId = uploadData.session_id;
      setSessionId(currentSessionId);

      // Step 2: Detect
      setActiveStep("detecting");
      const detectRes = await fetch(`${API_BASE}/detect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: currentSessionId,
          fault_types: faultTypes
        })
      });
      const detectData = await detectRes.json();
      setDetections(detectData.detections);
      setAnnotatedFrames(detectData.annotated_frame_urls);

      // Step 3: GEE
      setActiveStep("fetching_gee");
      const geeRes = await fetch(`${API_BASE}/gee`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat: 35.6,
          lng: 139.7,
          dataset_ids: geeDatasets
        })
      });
      const geeResultData = await geeRes.json();
      setGeeData(geeResultData);

      // Step 4: Analysis
      setActiveStep("generating_report");
      const analysisRes = await fetch(`${API_BASE}/analysis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          detections: detectData.detections,
          gee_data: geeResultData,
          fault_types: faultTypes
        })
      });
      const analysisData = await analysisRes.json();
      setReportText(analysisData.report_text);
      setFaultCounts(analysisData.fault_counts);
      setTotalCost(analysisData.total_cost);

    } catch (error) {
      console.error("Analysis Failed:", error);
      alert("Analysis failed. See console for details.");
    } finally {
      setIsLoading(false);
      setActiveStep(null);
    }
  };

  const generateSynthetic = async (generator, faultType) => {
    return fetch(`${API_BASE}/synthetic`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        generator,
        fault_type: faultType,
        count: 1
      })
    });
  };

  return {
    sessionId, uploadedFile, videoUrl,
    faultTypes, setFaultTypes,
    geeDatasets, setGeeDatasets,
    detections, annotatedFrames, geeData,
    reportText, faultCounts, totalCost,
    isLoading, activeStep,
    handleFileUpload, handleDrop, runAnalysis, generateSynthetic
  };
}
