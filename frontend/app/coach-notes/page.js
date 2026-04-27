'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/AuthProvider';
import { api } from '@/lib/api';

const STATUS_LABELS = {
  active: '进行中',
  recovering: '恢复中',
  resolved: '已恢复',
};

export default function CoachNotesPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [injuries, setInjuries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.push('/login');
      return;
    }
    api.coachNotes()
      .then(data => {
        setInjuries(data.injuries || []);
        setLoading(false);
      })
      .catch(e => {
        setError(e.message);
        setLoading(false);
      });
  }, [user, authLoading, router]);

  if (authLoading || loading) return <div className="text-gray-500 text-center py-20">读取教练笔记中...</div>;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">教练笔记</h1>
        <p className="text-sm text-gray-500 mt-1">这里展示 coach 已经沉淀的长期状态记录。</p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-400">
          {error}
        </div>
      )}

      <section className="space-y-3">
        <h2 className="text-gray-300 font-semibold">伤病记录</h2>
        {injuries.length === 0 ? (
          <div className="rounded-xl border border-gray-800 bg-gray-900 p-6 text-sm text-gray-500">
            暂无伤病记录。和教练聊到伤病后，系统会在这里展示沉淀结果。
          </div>
        ) : (
          <div className="space-y-3">
            {injuries.map(injury => (
              <div key={injury.id} className="rounded-xl border border-gray-800 bg-gray-900 p-5 space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-white font-medium">{injury.body_part}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      更新于 {formatDate(injury.updated_at)}
                    </div>
                  </div>
                  <span className="shrink-0 rounded-full border border-orange-500/30 bg-orange-500/10 px-2 py-0.5 text-xs text-orange-300">
                    {STATUS_LABELS[injury.status] || injury.status}
                  </span>
                </div>
                {injury.summary && (
                  <p className="text-sm text-gray-300 leading-relaxed">{injury.summary}</p>
                )}
                {injury.notes && (
                  <p className="text-sm text-gray-500 leading-relaxed whitespace-pre-wrap">{injury.notes}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function formatDate(value) {
  if (!value) return '未知';
  try {
    return new Date(value).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return String(value);
  }
}
