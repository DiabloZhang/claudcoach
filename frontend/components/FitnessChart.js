'use client';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts';

export default function FitnessChart({ data }) {
  // 只展示有数据的部分（过滤掉全0的早期日期）
  const trimmed = data.filter(d => d.ctl > 0 || d.atl > 0);
  // 每7天取一个标签避免拥挤
  const filtered = trimmed.filter((_, i) => i % 7 === 0 || i === trimmed.length - 1);

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={trimmed} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
        <XAxis
          dataKey="date"
          ticks={filtered.map(d => d.date)}
          tick={{ fill: '#6b7280', fontSize: 11 }}
        />
        <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} />
        <Tooltip
          contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 8 }}
          labelStyle={{ color: '#9ca3af' }}
        />
        <Legend wrapperStyle={{ color: '#9ca3af', fontSize: 12 }} />
        <ReferenceLine y={0} stroke="#374151" />
        <Line type="monotone" dataKey="ctl" name="体能 CTL" stroke="#60a5fa" dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="atl" name="疲劳 ATL" stroke="#fb923c" dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="tsb" name="状态 TSB" stroke="#34d399" dot={false} strokeWidth={1.5} strokeDasharray="4 2" />
      </LineChart>
    </ResponsiveContainer>
  );
}
