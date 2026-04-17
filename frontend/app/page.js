'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/AuthProvider';
import { api, setToken } from '@/lib/api';
import FitnessChart from '@/components/FitnessChart';
import BalanceChart from '@/components/BalanceChart';
import DailyActivities from '@/components/DailyActivities';

export default function Dashboard() {
  const router = useRouter();
  const { user, loading: authLoading, refreshUser } = useAuth();
  const [summary, setSummary] = useState(null);
  const [fitness, setFitness] = useState([]);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState('');
  const [syncDate, setSyncDate] = useState('');
  const [chartHeight, setChartHeight] = useState(420);
  const [showPasswordPrompt, setShowPasswordPrompt] = useState(false);

  const heightOptions = [
    { label: '矮', value: 420 },
    { label: '中', value: 840 },
  ];

  useEffect(() => {
    // 处理 Strava OAuth 回调带回的 token，立即清除 URL 参数避免 JWT 泄露
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const token = params.get('token');
      if (token) {
        // 用 history.replaceState 避免触发 Next.js RSC 重新获取
        window.history.replaceState({}, '', '/');
        setToken(token);
        refreshUser();
        return;
      }
    }
    if (authLoading) return;
    if (!user) {
      router.push('/login');
      return;
    }
    // Strava 登录用户若未设置密码，弹出一次性引导（仅在未显示时触发）
    if (!user.has_password && !showPasswordPrompt) {
      setShowPasswordPrompt(true);
    }
    loadData();
  }, [user, authLoading, showPasswordPrompt]);

  const loadData = () => {
    setLoading(true);
    Promise.all([
      api.summary(),
      api.fitness(),
      api.activities(30),
    ]).then(([s, f, a]) => {
      setSummary(s);
      setFitness(f);
      setActivities(a);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  const runSync = async (since = null) => {
    setSyncing(true);
    setSyncMsg('');
    try {
      if (since) {
        await api.syncFrom(since);
      } else {
        await api.sync();
      }
      await new Promise(r => setTimeout(r, 5000));
      await api.backfill();
      await api.calculateTss();
      await new Promise(r => setTimeout(r, 1000));
      loadData();
      setSyncMsg('同步完成');
    } catch {
      setSyncMsg('同步失败，请重试');
    } finally {
      setSyncing(false);
    }
  };

  if (authLoading || loading) return <div className="text-gray-500 text-center py-20">加载中...</div>;

  const { ctl, atl, tsb } = summary?.fitness ?? {};
  const balance = summary?.balance_28d ?? {};

  return (
    <div className="space-y-8">
      {/* 顶部操作栏 */}
      <div className="flex justify-end items-center gap-3 flex-wrap">
        {syncMsg && <span className="text-sm text-gray-400">{syncMsg}</span>}
        <input
          type="date"
          value={syncDate}
          onChange={e => setSyncDate(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-lg px-3 py-2"
        />
        <button
          onClick={() => syncDate ? runSync(syncDate) : alert('请选择日期')}
          disabled={syncing}
          className="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 text-white text-sm font-medium transition-colors"
        >
          同步指定日期
        </button>
        <button
          onClick={() => runSync()}
          disabled={syncing}
          className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm font-medium transition-colors"
        >
          {syncing ? '同步中...' : '立即同步'}
        </button>
      </div>

      {/* 体能状态卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
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

      {/* 最近活动（按天分组） */}
      <Section title="最近训练">
        <DailyActivities activities={activities} />
      </Section>

      {/* 未设置密码引导弹窗 */}
      {showPasswordPrompt && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
          <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6 max-w-sm w-full space-y-4">
            <h3 className="text-lg font-semibold text-white">安全提示</h3>
            <p className="text-gray-400 text-sm leading-relaxed">
              你当前通过 Strava 登录，尚未设置密码。
              {!user?.email && ' 建议先在「设置」中补充邮箱并设置密码，这样即使 Strava 授权失效也能正常登录。'}
              {user?.email && ' 建议前往「设置」中设置密码，这样即使 Strava 授权失效也能正常登录。'}
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => { setShowPasswordPrompt(false); router.push('/settings'); }}
                className="flex-1 bg-orange-500 hover:bg-orange-400 text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
              >
                去设置
              </button>
              <button
                onClick={() => setShowPasswordPrompt(false)}
                className="flex-1 bg-gray-800 hover:bg-gray-700 text-gray-300 font-medium py-2.5 rounded-lg transition-colors text-sm"
              >
                稍后再说
              </button>
            </div>
          </div>
        </div>
      )}
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
