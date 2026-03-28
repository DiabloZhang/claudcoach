'use client';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts';

const SPORT_ICON = {
  Ride: '🚴', VirtualRide: '🚴', Run: '🏃', TrailRun: '🏃',
  Swim: '🏊', OpenWaterSwim: '🏊',
};

function formatTime(seconds) {
  if (!seconds) return '--';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function CustomTooltip({ active, payload, label, activitiesByDate }) {
  if (!active || !payload?.length) return null;
  const ctl = payload.find(p => p.dataKey === 'ctl')?.value;
  const atl = payload.find(p => p.dataKey === 'atl')?.value;
  const tsb = payload.find(p => p.dataKey === 'tsb')?.value;
  const acts = activitiesByDate[label] || [];

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 text-xs min-w-[180px]">
      <div className="text-gray-400 mb-2">{label}</div>
      <div className="space-y-0.5 mb-2">
        <div className="text-blue-400">CTL {ctl?.toFixed(1)}</div>
        <div className="text-orange-400">ATL {atl?.toFixed(1)}</div>
        <div className={tsb >= 0 ? 'text-green-400' : 'text-red-400'}>TSB {tsb?.toFixed(1)}</div>
      </div>
      {acts.length > 0 && (
        <div className="border-t border-gray-700 pt-2 space-y-1.5">
          {acts.map((a, i) => (
            <div key={i}>
              <div className="text-gray-300">
                {SPORT_ICON[a.sport_type] || '●'} {a.name}
              </div>
              <div className="text-gray-500 pl-4">
                {formatTime(a.moving_time)}{a.tss ? ` · TSS ${a.tss}` : ''}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function FitnessChart({ data, height = 420, activities = [] }) {
  const trimmed = data.filter(d => d.ctl > 0 || d.atl > 0);
  const filtered = trimmed.filter((_, i) => i % 7 === 0 || i === trimmed.length - 1);

  // 按日期建索引（取 start_date 前10位 YYYY-MM-DD）
  const activitiesByDate = {};
  activities.forEach(a => {
    const dateStr = a.start_date_local || a.start_date;
    if (!dateStr) return;
    const d = dateStr.slice(0, 10);
    if (!activitiesByDate[d]) activitiesByDate[d] = [];
    activitiesByDate[d].push(a);
  });

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={trimmed} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
        <XAxis
          dataKey="date"
          ticks={filtered.map(d => d.date)}
          tick={{ fill: '#6b7280', fontSize: 11 }}
        />
        <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} />
        <Tooltip content={<CustomTooltip activitiesByDate={activitiesByDate} />} />
        <Legend wrapperStyle={{ color: '#9ca3af', fontSize: 12 }} />
        <ReferenceLine y={0} stroke="#374151" />
        <Line type="monotone" dataKey="ctl" name="体能 CTL" stroke="#60a5fa" dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="atl" name="疲劳 ATL" stroke="#fb923c" dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="tsb" name="状态 TSB" stroke="#34d399" dot={false} strokeWidth={1.5} strokeDasharray="4 2" />
      </LineChart>
    </ResponsiveContainer>
  );
}
