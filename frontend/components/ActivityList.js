const SPORT_EMOJI = { Swim: '🏊', Ride: '🚴', Run: '🏃', VirtualRide: '🚴' };
const SPORT_COLOR = { Swim: 'text-sky-400', Ride: 'text-orange-400', Run: 'text-violet-400', VirtualRide: 'text-orange-400' };

function formatDuration(sec) {
  if (!sec) return '--';
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function formatDistance(m, type) {
  if (!m) return '--';
  if (type === 'Swim') return `${Math.round(m)}m`;
  return `${(m / 1000).toFixed(1)}km`;
}

function formatDate(iso) {
  if (!iso) return '--';
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

export default function ActivityList({ activities }) {
  if (!activities?.length) return <div className="text-gray-600 text-sm">暂无数据</div>;

  return (
    <div className="space-y-2">
      {activities.map(a => (
        <div key={a.id} className="flex items-center gap-4 py-3 border-b border-gray-800 last:border-0">
          <span className="text-xl w-8">{SPORT_EMOJI[a.sport_type] ?? '🏅'}</span>
          <div className="flex-1 min-w-0">
            <div className={`font-medium text-sm truncate ${SPORT_COLOR[a.sport_type] ?? 'text-gray-300'}`}>
              {a.name}
            </div>
            <div className="text-gray-500 text-xs">{formatDate(a.start_date)}</div>
          </div>
          <div className="text-right text-sm">
            <div className="text-gray-300">{formatDistance(a.distance, a.sport_type)}</div>
            <div className="text-gray-500 text-xs">{formatDuration(a.moving_time)}</div>
          </div>
          {a.avg_heart_rate && (
            <div className="text-right text-sm w-16">
              <div className="text-red-400">{Math.round(a.avg_heart_rate)} bpm</div>
              <div className="text-gray-500 text-xs">心率</div>
            </div>
          )}
          {a.tss != null && (
            <div className="text-right text-sm w-14">
              <div className="text-yellow-400">{Math.round(a.tss)}</div>
              <div className="text-gray-500 text-xs">TSS</div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
