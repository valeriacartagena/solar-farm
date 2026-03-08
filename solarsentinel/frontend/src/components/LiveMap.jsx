import React, { useRef, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
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
    iconSize: [26, 38], iconAnchor: [13, 38], popupAnchor: [0, -40],
});

const icons = {
    critical: createIcon('#ef4444', '#ef4444'),
    moderate: createIcon('#f97316', '#f97316'),
    minor: createIcon('#eab308', '#eab308'),
};

// Re-centers the map when parsedCoords changes
function MapController({ lat, lng }) {
    const map = useMap();
    useEffect(() => { map.setView([lat, lng], 15); }, [lat, lng]);
    return null;
}

function SatelliteThumbnail({ thumbnailUrl, lat, lng }) {
    const map = useMap();
    useEffect(() => {
        if (!thumbnailUrl) return;
        const pad = 0.005;
        const bounds = [[lat - pad, lng - 0.007], [lat + pad, lng + 0.007]];
        const overlay = L.imageOverlay(thumbnailUrl, bounds, { opacity: 0.65 }).addTo(map);
        return () => map.removeLayer(overlay);
    }, [thumbnailUrl, lat, lng]);
    return null;
}

function satVal(v, unit = '') {
    return v != null ? `${Number(v).toFixed(1)}${unit}` : '—';
}

export function LiveMap({ state }) {
    const { detections, isLoading, geeData, parsedCoords } = state;
    const { lat, lng } = parsedCoords ? parsedCoords() : { lat: 35.6, lng: 139.7 };
    const center = [lat, lng];
    const thumbnailUrl = geeData?.thumbnail_url;

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
                    <MapController lat={lat} lng={lng} />
                    {thumbnailUrl && <SatelliteThumbnail thumbnailUrl={thumbnailUrl} lat={lat} lng={lng} />}

                    {detections.map((det, i) => (
                        <Marker key={i} position={[det.lat, det.lng]} icon={icons[det.severity] || icons.minor}>
                            <Popup maxWidth={260}>
                                <div style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 12, lineHeight: 1.8, minWidth: 200 }}>
                                    <p style={{ fontWeight: 700, fontSize: 13, marginBottom: 6 }}>{det.panel_id}</p>
                                    <p><span style={{ color: 'rgba(255,255,255,0.45)' }}>Fault: </span>{det.fault_type} ({det.severity})</p>

                                    {det.satellite_context && <>
                                        <hr style={{ border: 'none', borderTop: '1px solid rgba(255,255,255,0.1)', margin: '8px 0' }} />
                                        <p>🌡 {satVal(det.satellite_context.lst_celsius, '°C')} surface temp</p>
                                        <p>☀️ GHI {satVal(det.satellite_context.ghi_kwh_m2_day, ' kWh/m²/d')}</p>
                                        <p>🌿 NDVI {satVal(det.satellite_context.ndvi, '')} soiling index</p>
                                        <hr style={{ border: 'none', borderTop: '1px solid rgba(255,255,255,0.1)', margin: '8px 0' }} />
                                        <p>
                                            <span style={{ color: 'rgba(255,255,255,0.45)' }}>Ideal eff: </span>
                                            {satVal(det.satellite_context.ideal_efficiency_pct, '%')}
                                        </p>
                                        <p>
                                            <span style={{ color: '#ef4444' }}>Actual eff: </span>
                                            {satVal(det.satellite_context.actual_efficiency_pct, '%')}
                                            <span style={{ color: 'rgba(255,255,255,0.35)', fontSize: 11 }}>
                                                {' '}(−{satVal(det.satellite_context.fault_penalty_pct, '%')})
                                            </span>
                                        </p>
                                        {det.satellite_context.daily_energy_loss_kwh != null && (
                                            <p style={{ color: '#f97316' }}>
                                                ⚡ {det.satellite_context.daily_energy_loss_kwh} kWh/day lost
                                            </p>
                                        )}
                                    </>}

                                    <hr style={{ border: 'none', borderTop: '1px solid rgba(255,255,255,0.1)', margin: '8px 0' }} />
                                    <p style={{ color: '#22c55e', fontWeight: 700 }}>
                                        💰 ${det.cost_estimate} repair est.
                                    </p>
                                </div>
                            </Popup>
                        </Marker>
                    ))}
                </MapContainer>

                {/* Legend */}
                <div className="map-legend">
                    {[['#ef4444', 'Critical'], ['#f97316', 'Moderate'], ['#eab308', 'Minor']].map(([c, label]) => (
                        <div key={label} className="legend-item">
                            <div className="legend-dot" style={{ background: c }} />
                            <span>{label}</span>
                        </div>
                    ))}
                </div>

                {isLoading && (
                    <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000, background: 'rgba(10,10,20,0.6)', backdropFilter: 'blur(4px)' }}>
                        <div className="spinner" style={{ width: 44, height: 44, borderWidth: 3 }} />
                    </div>
                )}
            </div>
        </div>
    );
}
