'use client';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

const USER_ID = 1;

function formatDateTime(iso) {
  if (!iso) return '--';
  return new Date(iso + 'Z').toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function formatDate(iso) {
  if (!iso) return '--';
  return new Date(iso + 'Z').toLocaleDateString('zh-CN');
}

export default function SyncLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.syncLogs(USER_ID)
      .then(setLogs)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-gray-500 text-center py-20">加载中...</div>;
  if (!logs.length) return <div className="text-gray-500 text-center py-20">暂无同步记录</div>;

  return (
    <div className="space-y-4">
      <h1 className="text-gray-200 text-xl font-semibold">同步记录</h1>
      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-500 text-xs">
              <th className="text-left px-4 py-3">同步时间</th>
              <th className="text-left px-4 py-3">从哪天起</th>
              <th className="text-right px-4 py-3">新增</th>
              <th className="hidden sm:table-cell text-right px-4 py-3">跳过</th>
              <th className="hidden sm:table-cell text-right px-4 py-3">API 调用</th>
              <th className="hidden sm:table-cell text-right px-4 py-3">耗时</th>
              <th className="text-right px-4 py-3">状态</th>
            </tr>
          </thead>
          <tbody>
            {logs.map(log => (
              <tr key={log.id} className="border-b border-gray-800 last:border-0 hover:bg-gray-800/40">
                <td className="px-4 py-3 text-gray-300">{formatDateTime(log.started_at)}</td>
                <td className="px-4 py-3 text-gray-400">{formatDate(log.sync_from)}</td>
                <td className="px-4 py-3 text-right text-green-400">{log.activities_synced}</td>
                <td className="hidden sm:table-cell px-4 py-3 text-right text-gray-500">{log.activities_skipped}</td>
                <td className="hidden sm:table-cell px-4 py-3 text-right text-blue-400">{log.strava_api_calls}</td>
                <td className="hidden sm:table-cell px-4 py-3 text-right text-gray-400">{log.duration_seconds}s</td>
                <td className="px-4 py-3 text-right">
                  {log.status === 'success'
                    ? <span className="text-green-400">✓</span>
                    : <span className="text-red-400" title={log.error_message}>✗</span>
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
