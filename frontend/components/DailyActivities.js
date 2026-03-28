'use client';

const SPORT_COLOR = {
  Swim: { bg: 'bg-sky-500', text: 'text-sky-400', hex: '#38bdf8' },
  Ride: { bg: 'bg-orange-500', text: 'text-orange-400', hex: '#fb923c' },
  VirtualRide: { bg: 'bg-orange-500', text: 'text-orange-400', hex: '#fb923c' },
  Run: { bg: 'bg-violet-500', text: 'text-violet-400', hex: '#a78bfa' },
  TrailRun: { bg: 'bg-violet-500', text: 'text-violet-400', hex: '#a78bfa' },
};
const SPORT_EMOJI = { Swim: '🏊', Ride: '🚴', VirtualRide: '🚴', Run: '🏃', TrailRun: '🏃' };

const WEEKDAY = ['日', '一', '二', '三', '四', '五', '六'];

function localDate(iso) {
  // UTC+8
  const d = new Date(new Date(iso).getTime() + 8 * 3600 * 1000);
  return {
    key: d.toISOString().slice(0, 10),
    label: `${d.getMonth() + 1}月${d.getDate()}日 周${WEEKDAY[d.getDay()]}`,
  };
}

function formatDuration(sec) {
  if (!sec) return '--';
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function formatDistance(m, type) {
  if (!m) return null;
  if (type === 'Swim' || type === 'OpenWaterSwim') return `${Math.round(m)}m`;
  return `${(m / 1000).toFixed(1)}km`;
}

function bubbleSize(tss) {
  const base = tss ?? 30;
  return Math.round(Math.min(80, Math.max(32, 32 + (base / 150) * 48)));
}

function Bubble({ activity }) {
  const c = SPORT_COLOR[activity.sport_type] ?? { bg: 'bg-gray-600', hex: '#6b7280' };
  const size = bubbleSize(activity.tss);
  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className="rounded-full flex items-center justify-center text-white font-bold opacity-85"
        style={{ width: size, height: size, backgroundColor: c.hex, fontSize: size * 0.28 }}
      >
        {activity.tss != null ? Math.round(activity.tss) : SPORT_EMOJI[activity.sport_type] ?? '●'}
      </div>
      <div className="text-gray-500 text-xs">{SPORT_EMOJI[activity.sport_type] ?? '●'}</div>
    </div>
  );
}

function DayGroup({ date, activities }) {
  const dayTss = activities.reduce((s, a) => s + (a.tss ?? 0), 0);

  return (
    <div className="border-b border-gray-800 last:border-0 pb-5 mb-5 last:pb-0 last:mb-0">
      {/* 日期 + 当天总TSS */}
      <div className="flex justify-between items-center mb-3">
        <div className="text-gray-300 text-sm font-semibold">{date}</div>
        {dayTss > 0 && <div className="text-yellow-400 text-xs">TSS {Math.round(dayTss)}</div>}
      </div>

      {/* 气泡图 */}
      <div className="flex gap-4 items-end mb-4 pl-1">
        {activities.map((a, i) => <Bubble key={i} activity={a} />)}
      </div>

      {/* 活动列表 */}
      <div className="space-y-2">
        {activities.map(a => {
          const c = SPORT_COLOR[a.sport_type] ?? { text: 'text-gray-300' };
          const dist = formatDistance(a.distance, a.sport_type);
          return (
            <div key={a.id} className="flex items-center gap-3 pl-1">
              <div className="flex-1 min-w-0">
                <div className={`text-sm font-medium truncate ${c.text}`}>{a.name}</div>
                <div className="text-gray-500 text-xs">
                  {[dist, formatDuration(a.moving_time), a.avg_heart_rate ? `${Math.round(a.avg_heart_rate)} bpm` : null]
                    .filter(Boolean).join(' · ')}
                </div>
              </div>
              {a.tss != null && (
                <div className="text-yellow-400 text-sm font-medium w-10 text-right">{Math.round(a.tss)}</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function DailyActivities({ activities }) {
  if (!activities?.length) return <div className="text-gray-600 text-sm">暂无数据</div>;

  // 按本地日期分组
  const groups = {};
  const order = [];
  activities.forEach(a => {
    if (!a.start_date) return;
    const { key, label } = localDate(a.start_date);
    if (!groups[key]) { groups[key] = { label, items: [] }; order.push(key); }
    groups[key].items.push(a);
  });

  return (
    <div>
      {order.map(key => (
        <DayGroup key={key} date={groups[key].label} activities={groups[key].items} />
      ))}
    </div>
  );
}
