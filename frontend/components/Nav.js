'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from './AuthProvider';

const links = [
  { href: '/', label: 'Dashboard', icon: '📊' },
  { href: '/activities', label: '训练记录', icon: '🏅' },
  { href: '/coach', label: 'AI 教练', icon: '🤖' },
  { href: '/coach-notes', label: '教练笔记', icon: '📝' },
  { href: '/sync-logs', label: '同步', icon: '🔄' },
];

export default function Nav() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <>
      {/* 桌面顶部导航 */}
      <nav className="hidden sm:block border-b border-gray-800 bg-gray-900">
        <div className="max-w-6xl mx-auto px-4 flex items-center justify-between h-14">
          <div className="flex items-center gap-8">
            <span className="font-bold text-orange-400 text-lg">TriCoach</span>
            {links.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className={`text-sm font-medium transition-colors ${
                  pathname === href ? 'text-white' : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                {label}
              </Link>
            ))}
          </div>
          <div className="flex items-center gap-4">
            {user ? (
              <>
                <Link href="/settings" className="text-sm text-gray-400 hover:text-gray-200 transition-colors">
                  {user.nickname || user.name || '设置'}
                </Link>
                <button onClick={logout} className="text-sm text-gray-500 hover:text-gray-300 transition-colors">
                  退出
                </button>
              </>
            ) : (
              <Link href="/login" className="text-sm text-orange-400 hover:text-orange-300 transition-colors">
                登录
              </Link>
            )}
          </div>
        </div>
      </nav>

      {/* 手机顶部 logo 栏 */}
      <nav className="sm:hidden border-b border-gray-800 bg-gray-900">
        <div className="px-4 flex items-center justify-between h-12">
          <span className="font-bold text-orange-400 text-lg">TriCoach</span>
          {user ? (
            <Link href="/settings" className="text-sm text-gray-400">
              {user.nickname || user.name || '设置'}
            </Link>
          ) : (
            <Link href="/login" className="text-sm text-orange-400">
              登录
            </Link>
          )}
        </div>
      </nav>

      {/* 手机底部 Tab Bar */}
      <div className="sm:hidden fixed bottom-0 left-0 right-0 z-50 bg-gray-900 border-t border-gray-800">
        <div className="grid grid-cols-5">
          {links.map(({ href, label, icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`flex flex-col items-center justify-center py-2 gap-0.5 transition-colors ${
                  active ? 'text-orange-400' : 'text-gray-500'
                }`}
              >
                <span className="text-xl">{icon}</span>
                <span className="text-xs">{label}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </>
  );
}
