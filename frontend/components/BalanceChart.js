'use client';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const COLORS = { swim: '#38bdf8', bike: '#fb923c', run: '#a78bfa' };
const LABELS = { swim: '游泳', bike: '骑行', run: '跑步' };

export default function BalanceChart({ balance }) {
  const durationData = Object.entries(balance).map(([key, val]) => ({
    name: LABELS[key] || key,
    时长: Math.round(val.duration_min),
    color: COLORS[key],
  }));

  const distanceData = Object.entries(balance).map(([key, val]) => ({
    name: LABELS[key] || key,
    距离: Math.round(val.distance_km),
    color: COLORS[key],
  }));

  return (
    <div className="grid grid-cols-2 gap-6">
      <div>
        <div className="text-gray-500 text-xs mb-2">训练时长（分钟）</div>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={durationData} margin={{ left: -20 }}>
            <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 12 }} />
            <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} />
            <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 8 }} />
            <Bar dataKey="时长" radius={[4, 4, 0, 0]}>
              {durationData.map((d, i) => <Cell key={i} fill={d.color} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div>
        <div className="text-gray-500 text-xs mb-2">训练距离（km）</div>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={distanceData} margin={{ left: -20 }}>
            <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 12 }} />
            <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} />
            <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 8 }} />
            <Bar dataKey="距离" radius={[4, 4, 0, 0]}>
              {distanceData.map((d, i) => <Cell key={i} fill={d.color} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
