import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LineChart, Line } from 'recharts';

const COLORS = {
    hotspot: '#ef4444',
    'cracked cell': '#f97316',
    'dust accumulation': '#eab308',
};

function val(v, digits = 1, unit = '') {
    return v != null ? `${Number(v).toFixed(digits)}${unit}` : '—';
}

function IrradianceBadge({ label, value }) {
    return (
        <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.38)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 2 }}>{label}</div>
            <div style={{ fontSize: 17, fontWeight: 700, fontFamily: 'IBM Plex Mono, monospace', color: '#FFD166' }}>{val(value, 1)}</div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.28)' }}>kWh/m²/d</div>
        </div>
    );
}

function EffBar({ label, pct, color }) {
    return (
        <div style={{ marginBottom: 6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 3, color: 'rgba(255,255,255,0.5)' }}>
                <span>{label}</span>
                <span style={{ color, fontFamily: 'IBM Plex Mono, monospace', fontWeight: 600 }}>{val(pct, 1, '%')}</span>
            </div>
            <div style={{ height: 5, borderRadius: 3, background: 'rgba(255,255,255,0.07)', overflow: 'hidden' }}>
                <div style={{ width: `${Math.min(pct || 0, 100)}%`, height: '100%', background: color, borderRadius: 3, transition: 'width 0.6s ease' }} />
            </div>
        </div>
    );
}

export function AnalysisPanel({ state }) {
    const { reportText, detections, faultCounts, totalCost, isLoading, geeData } = state;
    const chartData = Object.entries(faultCounts).map(([name, value]) => ({ name, value }));

    const env = geeData?.environmental_conditions;
    const eff = geeData?.efficiency;
    const risks = geeData?.risk_flags;
    const isMock = geeData?.mock;

    // Sparkline from farm_summary
    const sparkData = (geeData?.farm_summary || [])
        .filter(r => r.ndvi != null || r.lst_celsius != null)
        .slice(-20)
        .map((r, i) => ({
            i,
            ndvi: r.ndvi != null ? parseFloat(r.ndvi.toFixed(3)) : null,
            lst: r.lst_celsius != null ? parseFloat(r.lst_celsius.toFixed(1)) : null,
        }));

    return (
        <div className="right-panel">
            <p className="panel-title">Analysis</p>

            {/* ── Irradiance row ────────────────────────────────────── */}
            {env && (
                <div style={{ marginBottom: 16 }}>
                    <div className="report-label">Irradiance (Global Solar Atlas)</div>
                    <div style={{ display: 'flex', justifyContent: 'space-around', background: 'rgba(255,209,102,0.06)', border: '1px solid rgba(255,209,102,0.15)', borderRadius: 10, padding: '12px 8px', marginBottom: 6 }}>
                        <IrradianceBadge label="GHI" value={env.ghi_kwh_m2_day} />
                        <div style={{ width: 1, background: 'rgba(255,255,255,0.06)' }} />
                        <IrradianceBadge label="DNI" value={env.dni_kwh_m2_day} />
                        <div style={{ width: 1, background: 'rgba(255,255,255,0.06)' }} />
                        <IrradianceBadge label="GTI" value={env.gti_kwh_m2_day} />
                    </div>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        {env.lst_celsius != null && (
                            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', background: 'rgba(255,255,255,0.05)', borderRadius: 6, padding: '3px 8px' }}>
                                🌡 {val(env.lst_celsius, 1, '°C')}
                            </span>
                        )}
                        {env.ndvi_mean != null && (
                            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', background: 'rgba(255,255,255,0.05)', borderRadius: 6, padding: '3px 8px' }}>
                                🌿 NDVI {val(env.ndvi_mean, 3)}
                            </span>
                        )}
                        {env.cloud_cover_pct != null && (
                            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', background: 'rgba(255,255,255,0.05)', borderRadius: 6, padding: '3px 8px' }}>
                                ☁ {val(env.cloud_cover_pct, 1, '%')} cloud
                            </span>
                        )}
                        {isMock && (
                            <span style={{ fontSize: 10, color: '#f97316', background: 'rgba(249,115,22,0.08)', borderRadius: 6, padding: '3px 8px', border: '1px solid rgba(249,115,22,0.2)' }}>
                                mock data
                            </span>
                        )}
                    </div>
                </div>
            )}

            {/* ── Efficiency bars ────────────────────────────────────── */}
            {eff && (
                <div style={{ marginBottom: 16 }}>
                    <div className="report-label">Panel Efficiency</div>
                    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 14px' }}>
                        <EffBar label="Nameplate" pct={eff.nameplate_efficiency_pct} color="rgba(255,255,255,0.25)" />
                        <EffBar label="Ideal (env)" pct={eff.ideal_efficiency_pct} color="#22c55e" />

                        {/* Loss breakdown */}
                        <div style={{ marginTop: 10, paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Efficiency losses</div>
                            {Object.entries(eff.loss_breakdown || {}).map(([key, v]) => (
                                <div key={key} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 2 }}>
                                    <span>{key.replace(/_/g, ' ').replace(' pct', '')}</span>
                                    <span style={{ color: '#ef4444', fontFamily: 'IBM Plex Mono, monospace' }}>−{val(v, 2, '%')}</span>
                                </div>
                            ))}
                        </div>

                        {/* Performance ratio */}
                        {eff.performance_ratio && (
                            <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                                <span style={{ color: 'rgba(255,255,255,0.4)' }}>Performance ratio</span>
                                <span style={{ color: '#FFD166', fontFamily: 'IBM Plex Mono, monospace', fontWeight: 700 }}>
                                    {val(eff.performance_ratio * 100, 1, '%')}
                                </span>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* ── Risk flags ────────────────────────────────────────── */}
            {risks && Object.values(risks).some(Boolean) && (
                <div style={{ marginBottom: 16 }}>
                    <div className="report-label">Risk Flags</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                        {Object.entries(risks).filter(([, v]) => v).map(([k]) => (
                            <div key={k} style={{ fontSize: 11.5, color: '#f97316', background: 'rgba(249,115,22,0.07)', border: '1px solid rgba(249,115,22,0.2)', borderRadius: 6, padding: '4px 10px' }}>
                                ⚠ {k.replace(/_risk$/, '').replace(/_/g, ' ')}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* ── AI Report ─────────────────────────────────────────── */}
            <div className="report-label">AI Report</div>
            <div className="report-box">
                {isLoading ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                        {[0.8, 1, 0.9, 0.6].map((w, i) => (
                            <div key={i} className="skeleton-line" style={{ width: `${w * 100}%` }} />
                        ))}
                    </div>
                ) : reportText || 'Upload a file and run analysis to see the AI-generated report here.'}
            </div>

            {/* ── Stat pills ────────────────────────────────────────── */}
            {totalCost > 0 && (
                <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
                    <div style={{ flex: 1, background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)', borderRadius: 10, padding: '10px 14px' }}>
                        <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'rgba(255,255,255,0.4)', marginBottom: 4 }}>Total Cost</div>
                        <div style={{ fontSize: 18, fontWeight: 700, color: '#ef4444', fontFamily: 'IBM Plex Mono,monospace' }}>${totalCost.toLocaleString()}</div>
                    </div>
                    <div style={{ flex: 1, background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)', borderRadius: 10, padding: '10px 14px' }}>
                        <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'rgba(255,255,255,0.4)', marginBottom: 4 }}>Faults</div>
                        <div style={{ fontSize: 18, fontWeight: 700, color: '#22c55e', fontFamily: 'IBM Plex Mono,monospace' }}>{detections.length}</div>
                    </div>
                </div>
            )}

            {/* ── Damage table ──────────────────────────────────────── */}
            <div className="report-label">Damage Table</div>
            <div className="damage-table">
                <div className="damage-table-header">
                    <div>Panel</div>
                    <div className="divider" />
                    <div>$ Cost</div>
                </div>
                <div className="damage-table-body">
                    {isLoading ? (
                        <div style={{ textAlign: 'center', padding: 16, color: 'rgba(255,255,255,0.3)', fontSize: 13 }}>Loading...</div>
                    ) : detections.length ? detections.map((det, i) => (
                        <div key={i} className="damage-row">
                            <div>{det.panel_id}</div>
                            <div className="divider" />
                            <div className="cost">${det.cost_estimate}</div>
                        </div>
                    )) : (
                        <div style={{ textAlign: 'center', padding: 16, color: 'rgba(255,255,255,0.25)', fontSize: 13 }}>No faults detected yet</div>
                    )}
                </div>
            </div>

            {/* ── Fault distribution bar chart ──────────────────────── */}
            {chartData.length > 0 && (
                <>
                    <div className="report-label" style={{ marginTop: 16 }}>Fault Distribution</div>
                    <div className="chart-area">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                                <XAxis dataKey="name" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11, fontFamily: 'IBM Plex Mono,monospace' }} axisLine={false} tickLine={false} />
                                <YAxis tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }} axisLine={false} tickLine={false} />
                                <Tooltip contentStyle={{ background: 'rgba(10,10,20,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 13 }} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
                                <Bar dataKey="value" radius={[5, 5, 0, 0]}>
                                    {chartData.map((entry, i) => <Cell key={i} fill={COLORS[entry.name] || '#22c55e'} />)}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </>
            )}

            {/* ── NDVI / LST sparkline ──────────────────────────────── */}
            {sparkData.length > 1 && (
                <>
                    <div className="report-label" style={{ marginTop: 16 }}>NDVI · LST Time-Series</div>
                    <div style={{ height: 100, background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, padding: '8px 0' }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={sparkData} margin={{ top: 4, right: 8, left: -30, bottom: 0 }}>
                                <XAxis dataKey="i" hide />
                                <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 9 }} axisLine={false} tickLine={false} />
                                <Tooltip
                                    contentStyle={{ background: 'rgba(10,10,20,0.9)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, fontSize: 11 }}
                                    labelFormatter={() => ''}
                                />
                                <Line type="monotone" dataKey="ndvi" dot={false} stroke="#22c55e" strokeWidth={1.5} name="NDVI" />
                                <Line type="monotone" dataKey="lst" dot={false} stroke="#f97316" strokeWidth={1.5} name="LST °C" />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </>
            )}
        </div>
    );
}
