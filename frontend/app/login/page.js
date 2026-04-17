'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/AuthProvider';
import { authApi, setToken } from '@/lib/api';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export default function LoginPage() {
  const router = useRouter();
  const { refreshUser } = useAuth();
  const [mode, setMode] = useState('login'); // login | register
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      let res;
      if (mode === 'login') {
        res = await authApi.login(email, password);
      } else {
        res = await authApi.register(email, password, nickname || undefined);
      }
      setToken(res.access_token);
      await refreshUser();
      router.push('/');
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const stravaLogin = () => {
    window.location.href = `${API_URL}/strava/login`;
  };

  return (
    <div className="min-h-[calc(100vh-8rem)] flex items-center justify-center px-4">
      <div className="w-full max-w-sm bg-gray-900 rounded-2xl border border-gray-800 p-8">
        <h1 className="text-2xl font-bold text-white text-center mb-2">
          {mode === 'login' ? '欢迎回来' : '创建账户'}
        </h1>
        <p className="text-gray-500 text-sm text-center mb-8">
          {mode === 'login' ? '登录你的 TriCoach 账户' : '注册开始你的铁三之旅'}
        </p>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'register' && (
            <div>
              <label className="block text-gray-400 text-sm mb-1.5">昵称</label>
              <input
                type="text"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-gray-100 text-sm focus:outline-none focus:border-orange-500"
                placeholder="你的昵称"
              />
            </div>
          )}
          <div>
            <label className="block text-gray-400 text-sm mb-1.5">邮箱</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-gray-100 text-sm focus:outline-none focus:border-orange-500"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="block text-gray-400 text-sm mb-1.5">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-gray-100 text-sm focus:outline-none focus:border-orange-500"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-orange-500 hover:bg-orange-400 disabled:bg-gray-700 disabled:text-gray-500 text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
          >
            {loading ? (mode === 'login' ? '登录中...' : '注册中...') : (mode === 'login' ? '登录' : '注册')}
          </button>
        </form>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-800" />
          </div>
          <div className="relative flex justify-center text-xs">
            <span className="bg-gray-900 px-2 text-gray-600">或用以下方式</span>
          </div>
        </div>

        <button
          onClick={stravaLogin}
          className="w-full flex items-center justify-center gap-2 bg-[#FC4C02] hover:bg-[#e04402] text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066m-7.008-5.599l2.836 5.598h4.172L10.477 0 5.611 12.343h4.172"/>
          </svg>
          使用 Strava 登录
        </button>

        <div className="mt-6 text-center text-sm text-gray-500">
          {mode === 'login' ? (
            <>
              还没有账户？{' '}
              <button onClick={() => setMode('register')} className="text-orange-400 hover:text-orange-300">
                立即注册
              </button>
            </>
          ) : (
            <>
              已有账户？{' '}
              <button onClick={() => setMode('login')} className="text-orange-400 hover:text-orange-300">
                立即登录
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
