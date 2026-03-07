import React from 'react';

export function DroneVideoPlayer({ state }) {
    const { videoUrl, annotatedFrames } = state;

    return (
        <div className="video-section">
            <p className="section-label">Drone Live Feed</p>
            <div className="video-box">
                {videoUrl
                    ? <video src={videoUrl} controls />
                    : (
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, opacity: 0.5 }}>
                            <svg width="40" height="40" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                                <path d="M15 10l4.553-2.069A1 1 0 0121 8.869v6.262a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                            </svg>
                            <span className="video-placeholder">Upload a drone video or image to begin</span>
                        </div>
                    )
                }
            </div>
            {annotatedFrames && annotatedFrames.length > 0 && (
                <div className="filmstrip">
                    {annotatedFrames.map((url, idx) => (
                        <img key={idx} src={`http://localhost:8000${url}`} alt={`frame ${idx}`} />
                    ))}
                </div>
            )}
        </div>
    );
}
