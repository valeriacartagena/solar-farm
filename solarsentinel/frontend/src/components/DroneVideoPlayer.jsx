import React from 'react';

export function DroneVideoPlayer({ state }) {
    const { videoUrl, annotatedFrames } = state;

    return (
        <div className="video-section">
            <p className="section-label">Drone live video play</p>
            <div className="video-box">
                {videoUrl
                    ? <video src={videoUrl} controls />
                    : <span className="video-placeholder">No video uploaded</span>
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
