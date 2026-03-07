import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const COLORS = { hotspot: '#ef4444', 'cracked cell': '#f97316', 'dust accumulation': '#eab308' };

export function AnalysisPanel({ state }) {
    const { reportText, detections, faultCounts, isLoading } = state;

    const chartData = Object.entries(faultCounts).map(([name, value]) => ({ name, value }));

    return (
        <div className="right-panel">
            <h2>Analysis</h2>

            <p className="report-label">Report summary:</p>
            <div className="report-box">
                {isLoading ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {[0.75, 1, 0.85, 0.5].map((w, i) => (
                            <div key={i} className="skeleton-line" style={{ width: `${w * 100}%` }} />
                        ))}
                    </div>
                ) : (
                    reportText || 'Awaiting scan instructions...'
                )}
            </div>

            <div className="damage-table" style={{ maxHeight: 240 }}>
                <div className="damage-table-header">
                    <div>Panel code</div>
                    <div className="divider" />
                    <div>$cost in damages</div>
                </div>
                <div className="damage-table-body">
                    {isLoading ? (
                        <p style={{ textAlign: 'center', padding: 16, color: '#6b7280', fontSize: 12 }}>Loading...</p>
                    ) : detections.length ? detections.map((det, i) => (
                        <div key={i} className="damage-row">
                            <div style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 12 }}>{det.panel_id}</div>
                            <div className="divider" />
                            <div className="cost" style={{ color: '#22c55e', fontFamily: 'IBM Plex Mono, monospace', fontSize: 12 }}>
                                ${det.cost_estimate}
                            </div>
                        </div>
                    )) : (
                        <p style={{ textAlign: 'center', padding: 16, color: '#6b7280', fontSize: 12 }}>No faults detected</p>
                    )}
                </div>
            </div>

            <div className="chart-area">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData}>
                        <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 10 }} axisLine={false} tickLine={false} />
                        <YAxis hide />
                        <Tooltip
                            contentStyle={{ background: '#1a1a1a', border: '1px solid #404040', borderRadius: 4 }}
                            itemStyle={{ color: '#fff' }}
                            cursor={{ fill: '#2d2d2d' }}
                        />
                        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
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
