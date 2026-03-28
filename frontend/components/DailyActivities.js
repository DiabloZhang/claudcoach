'use client';

const SPORT_COLOR = {
  Swim: { text: 'text-sky-400', hex: '#38bdf8' },
  OpenWaterSwim: { text: 'text-sky-400', hex: '#38bdf8' },
  Ride: { text: 'text-orange-400', hex: '#fb923c' },
  VirtualRide: { text: 'text-orange-400', hex: '#fb923c' },
  Run: { text: 'text-violet-400', hex: '#a78bfa' },
  TrailRun: { text: 'text-violet-400', hex: '#a78bfa' },
};
const SPORT_EMOJI = { Swim: '🏊', OpenWaterSwim: '🏊', Ride: '🚴', VirtualRide: '🚴', Run: '🏃', TrailRun: '🏃' };
const WEEKDAY = ['日', '一', '二', '三', '四', '五', '六'];

// 气泡排序：游泳 → 骑行 → 跑步
const BUBBLE_ORDER = ['Swim', 'OpenWaterSwim', 'Ride', 'VirtualRide', 'Run', 'TrailRun'];

function localDate(iso) {
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
  return Math.round(Math.min(72, Math.max(32, 32 + (tss / 150) * 40)));
}

function SportBubbles({ activities }) {
  // 按运动类型聚合 TSS，异常活动 TSS 计为 0
  const byType = {};
  activities.forEach(a => {
    if (a.is_excluded) return;  // 异常活动不计入气泡
    const key = a.sport_type;
    if (!byType[key]) byType[key] = { tss: 0, sport_type: key };
    byType[key].tss += a.tss ?? 0;
  });

  const bubbles = BUBBLE_ORDER
    .filter(t => byType[t])
    .map(t => byType[t]);

  // 去重（Swim/OpenWaterSwim 合并显示）
  const seen = new Set();
  const deduped = bubbles.filter(b => {
    const group = ['Swim', 'OpenWaterSwim'].includes(b.sport_type) ? 'swim'
      : ['Ride', 'VirtualRide'].includes(b.sport_type) ? 'ride' : 'run';
    if (seen.has(group)) return false;
    seen.add(group);
    return true;
  });

  return (
    <div className="flex gap-3 items-center justify-end flex-shrink-0">
      {deduped.map((b, i) => {
        const c = SPORT_COLOR[b.sport_type] ?? { hex: '#6b7280' };
        const size = bubbleSize(b.tss);
        return (
          <div key={i} className="flex flex-col items-center gap-1">
            <div
              className="rounded-full flex items-center justify-center text-white font-bold"
              style={{ width: size, height: size, backgroundColor: c.hex, fontSize: size * 0.26, opacity: 0.9 }}
            >
              {Math.round(b.tss)}
            </div>
            <div className="text-gray-500 text-xs">{SPORT_EMOJI[b.sport_type]}</div>
          </div>
        );
      })}
    </div>
  );
}

function DayGroup({ date, activities }) {
  // 异常活动 TSS 计为 0
  const dayTss = activities.reduce((s, a) => s + (a.is_excluded ? 0 : (a.tss ?? 0)), 0);

  return (
    <div className="border-b border-gray-800 last:border-0 py-4 last:pb-0">
      {/* 日期行 */}
      <div className="flex justify-between items-center mb-2">
        <div className="text-gray-300 text-sm font-semibold">{date}</div>
        {dayTss > 0 && <div className="text-yellow-400 text-xs">总 TSS {Math.round(dayTss)}</div>}
      </div>

      {/* 左：活动列表  右：气泡图 */}
      <div className="flex gap-4 items-center">
        <div className="flex-1 min-w-0 space-y-1.5">
          {activities.map(a => {
            const c = SPORT_COLOR[a.sport_type] ?? { text: 'text-gray-300' };
            const dist = formatDistance(a.distance, a.sport_type);
            const excluded = a.is_excluded;
            return (
              <div key={a.id} className={`flex items-center gap-2 ${excluded ? 'opacity-50' : ''}`}>
                <span className="text-base flex-shrink-0">{SPORT_EMOJI[a.sport_type] ?? '🏅'}</span>
                <div className="min-w-0 flex-1">
                  <div className={`text-sm truncate flex items-center gap-1.5 ${excluded ? 'text-gray-500' : c.text}`}>
                    <span className={excluded ? 'line-through' : ''}>{a.name}</span>
                    {excluded && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-red-900/60 text-red-400 font-medium flex-shrink-0">异常</span>
                    )}
                  </div>
                  <div className="text-gray-500 text-xs">
                    {excluded
                      ? (a.exclude_reason ?? '异常数据，TSS 不计入统计')
                      : [dist, formatDuration(a.moving_time)].filter(Boolean).join(' · ')}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        <SportBubbles activities={activities} />
      </div>
    </div>
  );
}

export default function DailyActivities({ activities }) {
  if (!activities?.length) return <div className="text-gray-600 text-sm">暂无数据</div>;

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
