'use client';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import FitnessChart from '@/components/FitnessChart';
import BalanceChart from '@/components/BalanceChart';
import ActivityList from '@/components/ActivityList';

const USER_ID = 1;

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [fitness, setFitness] = useState([]);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState('');
  const [chartHeight, setChartHeight] = useState(420);

  const heightOptions = [
    { label: '矮', value: 420 },
    { label: '中', value: 840 },
    { label: '高', value: 1680 },
    { label: '超高', value: 2520 },
  ];

  const loadData = () => {
    setLoading(true);
    Promise.all([
      api.summary(USER_ID),
      api.fitness(USER_ID),
      api.activities(USER_ID, 10),
    ]).then(([s, f, a]) => {
      setSummary(s);
      setFitness(f);
      setActivities(a);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  const handleSync = async () => {
    setSyncing(true);
    setSyncMsg('');
    try {
      await api.sync(USER_ID);
      // 等 5 秒让后台同步完成，再计算 TSS 并刷新
      await new Promise(r => setTimeout(r, 5000));
      await api.calculateTss(USER_ID);
      await new Promise(r => setTimeout(r, 1000));
      loadData();
      setSyncMsg('同步完成');
    } catch {
      setSyncMsg('同步失败，请重试');
    } finally {
      setSyncing(false);
    }
  };

  if (loading) return <div className="text-gray-500 text-center py-20">加载中...</div>;

  const { ctl, atl, tsb } = summary?.fitness ?? {};
  const balance = summary?.balance_28d ?? {};

  return (
    <div className="space-y-8">
      {/* 顶部操作栏 */}
      <div className="flex justify-end items-center gap-3">
        {syncMsg && <span className="text-sm text-gray-400">{syncMsg}</span>}
        <button
          onClick={handleSync}
          disabled={syncing}
          className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm font-medium transition-colors"
        >
          {syncing ? '同步中...' : '立即同步'}
        </button>
      </div>

      {/* 体能状态卡片 */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="体能 CTL" value={ctl?.toFixed(1)} desc="慢性训练负荷" color="text-blue-400" />
        <StatCard label="疲劳 ATL" value={atl?.toFixed(1)} desc="急性训练负荷" color="text-orange-400" />
        <StatCard
          label="状态 TSB"
          value={tsb?.toFixed(1)}
          desc={tsb >= 0 ? '状态良好，可以比赛' : '疲劳积累，注意恢复'}
          color={tsb >= 0 ? 'text-green-400' : 'text-red-400'}
        />
      </div>

      {/* CTL/ATL/TSB 趋势图 */}
      <Section title="体能趋势（近 90 天）" extra={
        <div className="flex gap-1">
          {heightOptions.map(o => (
            <button
              key={o.label}
              onClick={() => setChartHeight(o.value)}
              className={`px-2 py-1 rounded text-xs font-medium transition-colors ${chartHeight === o.value ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
            >
              {o.label}
            </button>
          ))}
        </div>
      }>
        <FitnessChart data={fitness} height={chartHeight} activities={activities} />
      </Section>

      {/* 三项训练量平衡 */}
      <Section title="训练量分布（近 28 天）">
        <BalanceChart balance={balance} />
      </Section>

      {/* 最近活动 */}
      <Section title="最近训练">
        <ActivityList activities={activities} />
      </Section>
    </div>
  );
}

function StatCard({ label, value, desc, color }) {
  return (
    <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
      <div className="text-gray-400 text-sm mb-1">{label}</div>
      <div className={`text-4xl font-bold ${color}`}>{value ?? '--'}</div>
      <div className="text-gray-500 text-xs mt-1">{desc}</div>
    </div>
  );
}

function Section({ title, children, extra }) {
  return (
    <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-gray-300 font-semibold">{title}</h2>
        {extra}
      </div>
      {children}
    </div>
  );
}
