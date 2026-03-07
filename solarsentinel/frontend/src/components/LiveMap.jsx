import React from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

delete L.Icon.Default.prototype._getIconUrl;

const createIcon = (color, glowColor) => L.divIcon({
    className: '',
    html: `<div style="filter: drop-shadow(0 0 6px ${glowColor})">
    <svg width="26" height="38" viewBox="0 0 26 38" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M13 0C5.82 0 0 5.82 0 13C0 22.75 13 38 13 38C13 38 26 22.75 26 13C26 5.82 20.18 0 13 0Z" fill="${color}"/>
      <circle cx="13" cy="13" r="5.5" fill="white" opacity="0.9"/>
    </svg>
  </div>`,
    iconSize: [26, 38],
    iconAnchor: [13, 38],
    popupAnchor: [0, -40],
});

const icons = {
    critical: createIcon('#ef4444', '#ef4444'),
    moderate: createIcon('#f97316', '#f97316'),
    minor: createIcon('#eab308', '#eab308'),
};

export function LiveMap({ state }) {
    const { detections, isLoading } = state;
    const center = [35.6, 139.7];

    return (
        <div className="map-section">
            <p className="section-label">Fault Detection Map</p>
            <div className="map-box">
                <MapContainer center={center} zoom={15} scrollWheelZoom style={{ height: '100%', width: '100%' }}>
                    <TileLayer
                        attribution='&copy; Esri'
                        url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                    />
                    {detections.map((det, i) => (
                        <Marker key={i} position={[det.lat, det.lng]} icon={icons[det.severity]}>
                            <Popup>
                                <div style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 12.5, padding: 4, lineHeight: 1.9, minWidth: 170 }}>
                                    <p style={{ fontWeight: 700, fontSize: 13, marginBottom: 4 }}>{det.panel_id}</p>
                                    <p><span style={{ color: 'rgba(255,255,255,0.5)' }}>Status: </span>{det.fault_type}</p>
                                    <p><span style={{ color: 'rgba(255,255,255,0.5)' }}>Score: </span>{(det.confidence * 100).toFixed(0)}%</p>
                                    <p style={{ color: '#22c55e', fontWeight: 700 }}><span style={{ color: 'rgba(255,255,255,0.5)', fontWeight: 400 }}>Cost: </span>${det.cost_estimate}</p>
                                </div>
                            </Popup>
                        </Marker>
                    ))}
                </MapContainer>

                <div className="map-legend">
                    {[['#ef4444', 'Critical'], ['#f97316', 'Moderate'], ['#eab308', 'Minor']].map(([c, label]) => (
                        <div key={label} className="legend-item">
                            <div className="legend-dot" style={{ background: c, boxShadow: `0 0 6px ${c}88` }} />
                            <span>{label}</span>
                        </div>
                    ))}
                </div>

                {isLoading && (
                    <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000, background: 'rgba(10,10,20,0.5)', backdropFilter: 'blur(4px)' }}>
                        <div className="spinner" style={{ width: 44, height: 44, borderWidth: 3 }} />
                    </div>
                )}
            </div>
        </div>
    );
}
