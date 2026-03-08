import React, { useRef, useState } from 'react';

export function DroneVideoPlayer({ state }) {
    const { videoUrl, annotatedFrames, pipelineResults, activeFaultIndex, setActiveFaultIndex } = state;
    const videoRef = useRef(null);
    const [viewMode, setViewMode] = useState('video'); // 'video' | 'inspect'

    const activeFault = pipelineResults && pipelineResults.length > 0 ? pipelineResults[activeFaultIndex] : null;
    const hasPipelineResults = pipelineResults && pipelineResults.length > 0;

    const seekToFault = (idx) => {
        setActiveFaultIndex(idx);
        setViewMode('inspect');
        const fault = pipelineResults[idx];
        if (videoRef.current && fault) {
            videoRef.current.currentTime = fault.timestamp_seconds;
            videoRef.current.pause();
        }
    };

    const handleResume = () => {
        setViewMode('video');
        if (videoRef.current) {
            videoRef.current.play();
        }
    };

    const handlePause = () => {
        setViewMode('inspect');
        if (videoRef.current) {
            videoRef.current.pause();
        }
    };

    const handlePrev = () => {
        if (activeFaultIndex > 0) seekToFault(activeFaultIndex - 1);
    };

    const handleNext = () => {
        if (activeFaultIndex < pipelineResults.length - 1) seekToFault(activeFaultIndex + 1);
    };

    const severityColor = { high: '#ef4444', medium: '#f97316', low: '#eab308' };
    const severityLabel = { high: 'High', medium: 'Medium', low: 'Low' };

    const navBtnStyle = {
        background: '#1e293b', color: '#e2e8f0', border: '1px solid #334155',
        borderRadius: 6, padding: '5px 14px', fontSize: 12, fontWeight: 600,
        cursor: 'pointer',
    };

    return (
        <div className="video-section">
            <p className="section-label">
                {hasPipelineResults
                    ? (viewMode === 'video' ? 'Drone Video Playback' : 'Fault Inspection')
                    : 'Drone live video play'}
            </p>

            {/* ── VIDEO MODE: full video player ── */}
            {(!hasPipelineResults || viewMode === 'video') && (
                <div className="video-box">
                    {videoUrl
                        ? <video ref={videoRef} src={videoUrl} controls style={{ width: '100%', borderRadius: 8 }} />
                        : <span className="video-placeholder">No video uploaded</span>
                    }
                </div>
            )}

            {/* ── INSPECT MODE: split view (frame + crop) ── */}
            {hasPipelineResults && viewMode === 'inspect' && activeFault && (
                <>
                    {/* Hidden video to keep ref alive for seeking */}
                    <video ref={videoRef} src={videoUrl} style={{ display: 'none' }} />

                    <div style={{ display: 'flex', gap: 10 }}>
                        {/* Left: Original frame with bbox */}
                        <div style={{ flex: 1, minWidth: 0 }}>
                            <p style={{ color: '#94a3b8', fontSize: 10, margin: '0 0 3px', fontWeight: 600 }}>
                                Original Frame @ {activeFault.timestamp_seconds}s
                            </p>
                            <div style={{ position: 'relative', background: '#0f0f23', borderRadius: 8, overflow: 'hidden' }}>
                                <img
                                    src={`http://localhost:8000${activeFault.frame_url}`}
                                    alt="Original frame"
                                    style={{ width: '100%', display: 'block', borderRadius: 8 }}
                                />
                                <div style={{
                                    position: 'absolute',
                                    left: `${activeFault.overshoot_fault.bbox.x_min * 100}%`,
                                    top: `${activeFault.overshoot_fault.bbox.y_min * 100}%`,
                                    width: `${(activeFault.overshoot_fault.bbox.x_max - activeFault.overshoot_fault.bbox.x_min) * 100}%`,
                                    height: `${(activeFault.overshoot_fault.bbox.y_max - activeFault.overshoot_fault.bbox.y_min) * 100}%`,
                                    border: `2px solid ${severityColor[activeFault.overshoot_fault.severity] || '#ef4444'}`,
                                    background: 'rgba(239, 68, 68, 0.1)',
                                    borderRadius: 3,
                                    pointerEvents: 'none',
                                    animation: 'pulse-border 1.5s ease-in-out infinite',
                                }} />
                            </div>
                        </div>

                        {/* Right: Zoomed crop with YOLO */}
                        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
                            <p style={{ color: '#a5b4fc', fontSize: 10, margin: '0 0 3px', fontWeight: 600 }}>
                                Zoomed-In — YOLOv8 Detection
                            </p>
                            <div style={{
                                background: '#0f0f23', borderRadius: 8, overflow: 'hidden',
                                display: 'flex', flexDirection: 'column', flex: 1,
                            }}>
                                <img
                                    src={`http://localhost:8000${activeFault.annotated_crop_url}`}
                                    alt="YOLO annotated crop"
                                    style={{ width: '100%', display: 'block', borderRadius: '8px 8px 0 0', objectFit: 'contain' }}
                                />
                                <div style={{ padding: 8, flex: 1 }}>
                                    {activeFault.yolo_detections.length > 0 ? (
                                        activeFault.yolo_detections.map((det, i) => (
                                            <div key={i} style={{
                                                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                                background: '#16213e', borderRadius: 5, padding: '5px 10px',
                                                marginBottom: 4, fontSize: 12, color: '#e2e8f0',
                                            }}>
                                                <span style={{ fontWeight: 700 }}>{det.class_name}</span>
                                                <span style={{
                                                    color: det.confidence > 0.7 ? '#22c55e' : det.confidence > 0.4 ? '#eab308' : '#ef4444',
                                                    fontWeight: 600,
                                                }}>
                                                    {(det.confidence * 100).toFixed(0)}%
                                                </span>
                                            </div>
                                        ))
                                    ) : (
                                        <p style={{ color: '#64748b', fontSize: 11, margin: 0, textAlign: 'center' }}>
                                            Region flagged by AI Vision — no YOLO match
                                        </p>
                                    )}
                                    <div style={{
                                        marginTop: 6, padding: '5px 8px',
                                        background: '#1a1a2e', borderRadius: 5,
                                        fontSize: 11, color: '#94a3b8', lineHeight: 1.4,
                                    }}>
                                        <span style={{
                                            color: severityColor[activeFault.overshoot_fault.severity],
                                            fontWeight: 700, fontSize: 10, textTransform: 'uppercase',
                                            marginRight: 6,
                                        }}>
                                            {severityLabel[activeFault.overshoot_fault.severity] || 'Unknown'} severity
                                        </span>
                                        {activeFault.overshoot_fault.description}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </>
            )}

            {/* ── Controls ── */}
            {hasPipelineResults && (
                <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    gap: 8, margin: '8px 0',
                }}>
                    <button onClick={handlePrev} disabled={activeFaultIndex === 0} style={{
                        ...navBtnStyle, opacity: activeFaultIndex === 0 ? 0.4 : 1,
                    }}>
                        Prev
                    </button>

                    {viewMode === 'inspect' ? (
                        <button onClick={handleResume} style={{
                            ...navBtnStyle, background: '#22c55e', color: '#fff', minWidth: 130,
                        }}>
                            Resume Video
                        </button>
                    ) : (
                        <button onClick={handlePause} style={{
                            ...navBtnStyle, background: '#6366f1', color: '#fff', minWidth: 130,
                        }}>
                            Inspect Fault
                        </button>
                    )}

                    <button onClick={handleNext} disabled={activeFaultIndex === pipelineResults.length - 1} style={{
                        ...navBtnStyle, opacity: activeFaultIndex === pipelineResults.length - 1 ? 0.4 : 1,
                    }}>
                        Next
                    </button>

                    <span style={{ color: '#64748b', fontSize: 11, marginLeft: 6 }}>
                        {activeFaultIndex + 1} / {pipelineResults.length} faults
                    </span>
                </div>
            )}

            {/* ── Fault filmstrip ── */}
            {hasPipelineResults && (
                <div style={{
                    display: 'flex', gap: 6, overflowX: 'auto',
                    marginTop: 4, padding: '4px 0',
                }}>
                    {pipelineResults.map((fault, idx) => (
                        <div
                            key={idx}
                            onClick={() => seekToFault(idx)}
                            style={{
                                cursor: 'pointer',
                                border: idx === activeFaultIndex ? '2px solid #6366f1' : '2px solid #1e293b',
                                borderRadius: 6, overflow: 'hidden', minWidth: 100,
                                background: '#16213e',
                                transition: 'border-color 0.2s, transform 0.15s',
                                transform: idx === activeFaultIndex ? 'scale(1.05)' : 'scale(1)',
                            }}
                        >
                            <img
                                src={`http://localhost:8000${fault.crop_url}`}
                                alt={`fault ${idx}`}
                                style={{ width: 100, height: 65, objectFit: 'cover', display: 'block' }}
                            />
                            <div style={{
                                padding: '3px 6px', fontSize: 10,
                                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                            }}>
                                <span style={{ color: '#e2e8f0', fontWeight: 600 }}>
                                    {fault.overshoot_fault.fault_type}
                                </span>
                                <span style={{
                                    padding: '1px 5px', borderRadius: 3, fontSize: 9, fontWeight: 600,
                                    background: severityColor[fault.overshoot_fault.severity] || '#eab308',
                                    color: '#fff',
                                }}>
                                    {fault.overshoot_fault.severity}
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Legacy filmstrip */}
            {!hasPipelineResults && annotatedFrames && annotatedFrames.length > 0 && (
                <div className="filmstrip">
                    {annotatedFrames.map((url, idx) => (
                        <img key={idx} src={`http://localhost:8000${url}`} alt={`frame ${idx}`} />
                    ))}
                </div>
            )}

            <style>{`
                @keyframes pulse-border {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.4; }
                }
            `}</style>
        </div>
    );
}
