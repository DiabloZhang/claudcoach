'use client';
import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useAuth } from '@/components/AuthProvider';
import { authApi } from '@/lib/api';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

function SettingsContent() {
  const { user, refreshUser } = useAuth();
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState('profile');
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (searchParams.get('strava') === 'linked') {
      // 使用 setTimeout 避免同步 setState 触发 cascading renders 警告
      setTimeout(() => {
        setMsg('Strava 绑定成功！');
        refreshUser();
      }, 0);
    }
  }, [searchParams]);

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-white">设置</h1>

      {(msg || error) && (
        <div className={`p-3 rounded-lg text-sm ${msg ? 'bg-green-500/10 border border-green-500/20 text-green-400' : 'bg-red-500/10 border border-red-500/20 text-red-400'}`}>
          {msg || error}
        </div>
      )}

      {/* Tab 切换 */}
      <div className="flex gap-2 border-b border-gray-800">
        {[
          { id: 'profile', label: '个人资料' },
          { id: 'password', label: '密码' },
          { id: 'data', label: '数据源' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => { setActiveTab(tab.id); setMsg(''); setError(''); }}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'text-orange-400 border-b-2 border-orange-400'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'profile' && <ProfileTab user={user} onMsg={setMsg} onError={setError} onRefresh={refreshUser} />}
      {activeTab === 'password' && <PasswordTab onMsg={setMsg} onError={setError} hasPassword={!!user?.has_password} userEmail={user?.email} />}
      {activeTab === 'data' && <DataSourceTab user={user} onMsg={setMsg} onError={setError} onRefresh={refreshUser} />}
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense fallback={<div className="text-gray-500 text-center py-20">加载中...</div>}>
      <SettingsContent />
    </Suspense>
  );
}

function ProfileTab({ user, onMsg, onError, onRefresh }) {
  const [nickname, setNickname] = useState(user?.nickname || '');
  const [email, setEmail] = useState(user?.email || '');
  const [timezone, setTimezone] = useState(user?.timezone || 'Asia/Shanghai');
  const [sleepTime, setSleepTime] = useState(user?.sleep_time || '22:00');
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    setLoading(true);
    onError('');
    onMsg('');
    try {
      await authApi.updateProfile({ nickname, email: email || undefined, timezone, sleep_time: sleepTime });
      onMsg('资料已更新');
      onRefresh();
    } catch (e) {
      onError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 space-y-4">
      <div>
        <label className="block text-gray-400 text-sm mb-1.5">昵称</label>
        <input
          type="text"
          value={nickname}
          onChange={e => setNickname(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-gray-100 text-sm focus:outline-none focus:border-orange-500"
        />
      </div>
      <div>
        <label className="block text-gray-400 text-sm mb-1.5">邮箱</label>
        <input
          type="email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder={user?.email ? '' : '尚未绑定邮箱'}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-gray-100 text-sm focus:outline-none focus:border-orange-500"
        />
        {!user?.email && (
          <p className="text-xs text-gray-500 mt-1.5">绑定邮箱后，可用邮箱+密码方式登录。</p>
        )}
      </div>
      <div>
        <label className="block text-gray-400 text-sm mb-1.5">时区</label>
        <select
          value={timezone}
          onChange={e => setTimezone(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-gray-100 text-sm focus:outline-none focus:border-orange-500"
        >
          <option value="Asia/Shanghai">Asia/Shanghai (北京时间)</option>
          <option value="Asia/Tokyo">Asia/Tokyo (东京时间)</option>
          <option value="Asia/Singapore">Asia/Singapore (新加坡时间)</option>
          <option value="Europe/London">Europe/London (伦敦时间)</option>
          <option value="Europe/Paris">Europe/Paris (巴黎时间)</option>
          <option value="America/New_York">America/New_York (纽约时间)</option>
          <option value="America/Los_Angeles">America/Los_Angeles (洛杉矶时间)</option>
          <option value="Australia/Sydney">Australia/Sydney (悉尼时间)</option>
        </select>
      </div>
      <div>
        <label className="block text-gray-400 text-sm mb-1.5">睡眠时间</label>
        <input
          type="time"
          value={sleepTime}
          onChange={e => setSleepTime(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-gray-100 text-sm focus:outline-none focus:border-orange-500"
        />
      </div>
      <button
        onClick={handleSave}
        disabled={loading}
        className="bg-orange-500 hover:bg-orange-400 disabled:bg-gray-700 text-white font-medium py-2.5 rounded-lg transition-colors text-sm px-6"
      >
        {loading ? '保存中...' : '保存'}
      </button>
    </div>
  );
}

function PasswordTab({ onMsg, onError, hasPassword, userEmail }) {
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = async () => {
    onError('');
    onMsg('');
    if (newPassword !== confirmPassword) {
      onError('两次输入的密码不一致');
      return;
    }
    if (newPassword.length < 6) {
      onError('密码至少需要 6 位');
      return;
    }
    setLoading(true);
    try {
      await authApi.changePassword(oldPassword || undefined, newPassword);
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
      onMsg(hasPassword ? '密码已修改' : '密码已设置');
    } catch (e) {
      onError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 space-y-4">
      {!hasPassword && (
        <div className="text-sm text-yellow-400 bg-yellow-400/10 border border-yellow-400/20 rounded-lg p-3">
          你当前使用 Strava 登录，尚未设置密码。
          {!userEmail && ' 建议先在「个人资料」中补充邮箱，再设置密码，这样以后可以用邮箱+密码登录。'}
          {userEmail && ' 设置密码后，即可用邮箱+密码登录。'}
        </div>
      )}
      {hasPassword && (
        <div>
          <label className="block text-gray-400 text-sm mb-1.5">原密码</label>
          <input
            type="password"
            value={oldPassword}
            onChange={e => setOldPassword(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-gray-100 text-sm focus:outline-none focus:border-orange-500"
          />
        </div>
      )}
      <div>
        <label className="block text-gray-400 text-sm mb-1.5">新密码</label>
        <input
          type="password"
          value={newPassword}
          onChange={e => setNewPassword(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-gray-100 text-sm focus:outline-none focus:border-orange-500"
        />
      </div>
      <div>
        <label className="block text-gray-400 text-sm mb-1.5">确认新密码</label>
        <input
          type="password"
          value={confirmPassword}
          onChange={e => setConfirmPassword(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-gray-100 text-sm focus:outline-none focus:border-orange-500"
        />
      </div>
      <button
        onClick={handleChange}
        disabled={loading}
        className="bg-orange-500 hover:bg-orange-400 disabled:bg-gray-700 text-white font-medium py-2.5 rounded-lg transition-colors text-sm px-6"
      >
        {loading ? (hasPassword ? '修改中...' : '设置中...') : (hasPassword ? '修改密码' : '设置密码')}
      </button>
    </div>
  );
}

function DataSourceTab({ user, onMsg, onError, onRefresh }) {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadSources = async () => {
    try {
      const data = await authApi.getDataSources();
      setSources(data);
    } catch (e) {
      onError(e.message);
    }
  };

  useEffect(() => {
    loadSources();
  }, []);

  const handleConnectStrava = () => {
    // 获取当前 token 作为 state 传给后端，用于绑定
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : '';
    const url = new URL(`${API_URL}/strava/login`);
    if (token) url.searchParams.set('state', token);
    window.location.href = url.toString();
  };

  const handleDisconnectStrava = async () => {
    setLoading(true);
    onError('');
    try {
      await authApi.disconnectStrava();
      onMsg('已解除 Strava 绑定');
      onRefresh();
    } catch (e) {
      onError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 space-y-6">
      {/* Strava */}
      <div>
        <h3 className="text-gray-200 font-medium mb-3">Strava</h3>
        {user?.has_strava ? (
          <div className="flex items-center justify-between bg-gray-800 rounded-lg p-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-[#FC4C02] flex items-center justify-center text-white text-xs font-bold">
                S
              </div>
              <div>
                <div className="text-sm text-gray-200">已绑定 Strava</div>
                <div className="text-xs text-gray-500">授权类型: {user.auth_provider}</div>
              </div>
            </div>
            <button
              onClick={handleDisconnectStrava}
              disabled={loading}
              className="text-sm text-red-400 hover:text-red-300 border border-red-500/30 hover:border-red-500/50 rounded-lg px-3 py-1.5 transition-colors"
            >
              解除绑定
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-gray-500">绑定 Strava 账户以同步训练数据</p>
            <button
              onClick={handleConnectStrava}
              className="flex items-center gap-2 bg-[#FC4C02] hover:bg-[#e04402] text-white font-medium py-2.5 px-4 rounded-lg transition-colors text-sm"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066m-7.008-5.599l2.836 5.598h4.172L10.477 0 5.611 12.343h4.172"/>
              </svg>
              绑定 Strava
            </button>
          </div>
        )}
      </div>

      {/* 其他数据源 */}
      <div>
        <h3 className="text-gray-200 font-medium mb-3">其他数据源</h3>
        {sources.length === 0 ? (
          <p className="text-sm text-gray-500">暂无其他数据源配置</p>
        ) : (
          <div className="space-y-2">
            {sources.map(s => (
              <div key={s.id} className="flex items-center justify-between bg-gray-800 rounded-lg p-3">
                <div className="text-sm text-gray-300">{s.provider}</div>
                <button
                  onClick={async () => {
                    try {
                      await authApi.deleteDataSource(s.id);
                      loadSources();
                    } catch (e) {
                      onError(e.message);
                    }
                  }}
                  className="text-xs text-red-400 hover:text-red-300"
                >
                  删除
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
