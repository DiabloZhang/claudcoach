'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const links = [
  { href: '/', label: 'Dashboard', icon: '📊' },
  { href: '/activities', label: '训练记录', icon: '🏅' },
  { href: '/coach', label: 'AI 教练', icon: '🤖' },
  { href: '/sync-logs', label: '同步', icon: '🔄' },
];

export default function Nav() {
  const pathname = usePathname();
  return (
    <>
      {/* 桌面顶部导航 */}
      <nav className="hidden sm:block border-b border-gray-800 bg-gray-900">
        <div className="max-w-6xl mx-auto px-4 flex items-center gap-8 h-14">
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
      </nav>

      {/* 手机顶部 logo 栏 */}
      <nav className="sm:hidden border-b border-gray-800 bg-gray-900">
        <div className="px-4 flex items-center h-12">
          <span className="font-bold text-orange-400 text-lg">TriCoach</span>
        </div>
      </nav>

      {/* 手机底部 Tab Bar */}
      <div className="sm:hidden fixed bottom-0 left-0 right-0 z-50 bg-gray-900 border-t border-gray-800">
        <div className="grid grid-cols-4">
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
