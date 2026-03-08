import React from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

delete L.Icon.Default.prototype._getIconUrl;

const createIcon = (color) => L.divIcon({
    className: '',
    html: `<svg width="24" height="36" viewBox="0 0 24 36" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 0C5.373 0 0 5.373 0 12C0 21 12 36 12 36C12 36 24 21 24 12C24 5.373 18.627 0 12 0Z" fill="${color}"/>
    <circle cx="12" cy="12" r="5" fill="white"/>
  </svg>`,
    iconSize: [24, 36],
    iconAnchor: [12, 36],
    popupAnchor: [0, -38],
});

const icons = {
    critical: createIcon('#ef4444'),
    moderate: createIcon('#f97316'),
    minor: createIcon('#eab308'),
};

export function LiveMap({ state }) {
    const { detections, isLoading } = state;
    const center = [35.6, 139.7];

    return (
        <div className="map-section">
            <p className="section-label">Live map finding faulty panels</p>
            <div className="map-box">
                <MapContainer center={center} zoom={15} scrollWheelZoom
                    style={{ height: '100%', width: '100%' }}>
                    <TileLayer
                        attribution='&copy; Esri'
                        url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                    />
                    {detections.map((det, i) => (
                        <Marker key={i} position={[det.lat, det.lng]} icon={icons[det.severity]}>
                            <Popup>
                                <div style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 12, background: '#000', color: '#fff', padding: 8, margin: -12, minWidth: 160 }}>
                                    <p><strong>Panel #</strong> {det.panel_id}</p>
                                    <p><strong>Status:</strong> {det.fault_type}</p>
                                    <p><strong>Damages:</strong> {det.description}</p>
                                    <p><strong>Score:</strong> {(det.confidence * 100).toFixed(0)}%</p>
                                    <p style={{ color: '#22c55e' }}><strong>Cost:</strong> ${det.cost_estimate}</p>
                                </div>
                            </Popup>
                        </Marker>
                    ))}
                </MapContainer>

                <div className="map-legend">
                    {[['#ef4444', 'Critical'], ['#f97316', 'Moderate'], ['#eab308', 'Minor']].map(([c, label]) => (
                        <div key={label} className="legend-item">
                            <div className="legend-dot" style={{ background: c }} />
                            <span>{label}</span>
                        </div>
                    ))}
                </div>

                {isLoading && (
                    <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000, pointerEvents: 'none' }}>
                        <div className="spinner" style={{ width: 48, height: 48, borderWidth: 4, borderColor: '#22c55e', borderTopColor: 'transparent' }} />
                    </div>
                )}
            </div>
        </div>
    );
}
