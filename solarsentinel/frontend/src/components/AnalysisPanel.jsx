import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const COLORS = {
    hotspot: '#ef4444',
    'cracked cell': '#f97316',
    'dust accumulation': '#eab308'
};

export function AnalysisPanel({ state }) {
    const { reportText, detections, faultCounts, totalCost, isLoading } = state;
    const chartData = Object.entries(faultCounts).map(([name, value]) => ({ name, value }));

    return (
        <div className="right-panel">
            <p className="panel-title">Analysis</p>

            {/* Summary */}
            <div className="report-label">Report Summary</div>
            <div className="report-box">
                {isLoading ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                        {[0.8, 1, 0.9, 0.6].map((w, i) => (
                            <div key={i} className="skeleton-line" style={{ width: `${w * 100}%` }} />
                        ))}
                    </div>
                ) : (
                    reportText || 'Upload a file and run analysis to see the AI-generated report here.'
                )}
            </div>

            {/* Total cost pill */}
            {totalCost > 0 && (
                <div style={{ marginBottom: 16, display: 'flex', gap: 10 }}>
                    <div style={{ flex: 1, background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)', borderRadius: 10, padding: '10px 14px' }}>
                        <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'rgba(255,255,255,0.4)', marginBottom: 4 }}>Total Cost</div>
                        <div style={{ fontSize: 18, fontWeight: 700, color: '#ef4444', fontFamily: 'IBM Plex Mono, monospace' }}>${totalCost.toLocaleString()}</div>
                    </div>
                    <div style={{ flex: 1, background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)', borderRadius: 10, padding: '10px 14px' }}>
                        <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'rgba(255,255,255,0.4)', marginBottom: 4 }}>Faults Found</div>
                        <div style={{ fontSize: 18, fontWeight: 700, color: '#22c55e', fontFamily: 'IBM Plex Mono, monospace' }}>{detections.length}</div>
                    </div>
                </div>
            )}

            {/* Damage table */}
            <div className="report-label">Damage Table</div>
            <div className="damage-table">
                <div className="damage-table-header">
                    <div>Panel Code</div>
                    <div className="divider" />
                    <div>$ Cost</div>
                </div>
                <div className="damage-table-body">
                    {isLoading ? (
                        <div style={{ display: 'flex', justifyContent: 'center', padding: 16, color: 'rgba(255,255,255,0.3)', fontSize: 13 }}>Loading faults...</div>
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

            {/* Chart */}
            <div className="report-label" style={{ marginTop: 16 }}>Fault Distribution</div>
            <div className="chart-area">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                        <XAxis
                            dataKey="name"
                            tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11, fontFamily: 'IBM Plex Mono, monospace' }}
                            axisLine={false} tickLine={false}
                        />
                        <YAxis
                            tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }}
                            axisLine={false} tickLine={false}
                        />
                        <Tooltip
                            contentStyle={{ background: 'rgba(10,10,20,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 13 }}
                            itemStyle={{ color: '#fff' }}
                            labelStyle={{ color: 'rgba(255,255,255,0.5)', fontSize: 11 }}
                            cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                        />
                        <Bar dataKey="value" radius={[5, 5, 0, 0]}>
                            {chartData.map((entry, i) => (
                                <Cell key={i} fill={COLORS[entry.name] || '#22c55e'} />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
