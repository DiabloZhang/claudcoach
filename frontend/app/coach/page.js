'use client';
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useAuth } from '@/components/AuthProvider';
import { api } from '@/lib/api';

const TOPIC_LABELS = {
  injury: '伤病',
  recovery: '恢复',
  schedule: '日程',
  goal: '目标',
};

export default function CoachPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [convId, setConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [model, setModel] = useState(null);
  const [providerOrder, setProviderOrder] = useState(['gemini', 'anthropic']);
  const [topics, setTopics] = useState([]);
  const [showInfo, setShowInfo] = useState(false);
  const [modelLogs, setModelLogs] = useState([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [avatarUrl, setAvatarUrl] = useState(null);
  const [starting, setStarting] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.push('/login');
      return;
    }
    Promise.all([
      api.coachOpen(),
      api.coachModelPreference().catch(() => null),
    ]).then(([data, pref]) => {
      setConvId(data.conversation_id);
      setMessages(data.messages);
      if (data.model) setModel(data.model);
      if (data.avatar_url) setAvatarUrl(data.avatar_url);
      if (data.topics) setTopics(data.topics);
      if (pref?.provider_order) setProviderOrder(pref.provider_order);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [user, authLoading, router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setInput('');
    setSending(true);
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    try {
      const res = await api.coachMessage(convId, text);
      setMessages(prev => [...prev, { role: 'coach', content: res.reply }]);
      if (res.model) setModel(res.model);
      if (res.avatar_url) setAvatarUrl(res.avatar_url);
      if (res.topics) setTopics(res.topics);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'coach', content: `出错了：${e.message}` }]);
    } finally {
      setSending(false);
    }
  };

  const startNew = async () => {
    setStarting(true);
    try {
      const data = await api.coachNew();
      setConvId(data.conversation_id);
      setMessages(data.messages);
      setTopics(data.topics || []);
      if (data.model) setModel(data.model);
      if (data.avatar_url) setAvatarUrl(data.avatar_url);
    } catch (e) {
      alert('开启新对话失败：' + e.message);
    } finally {
      setStarting(false);
    }
  };

  const updateProviderPreference = async (primary) => {
    const next = primary === 'anthropic'
      ? ['anthropic', 'gemini']
      : ['gemini', 'anthropic'];
    setProviderOrder(next);
    try {
      const pref = await api.updateCoachModelPreference(next);
      if (pref?.provider_order) setProviderOrder(pref.provider_order);
    } catch (e) {
      alert('模型优先级保存失败：' + e.message);
    }
  };

  const loadLogs = async () => {
    if (!convId) return;
    setLogsLoading(true);
    try {
      const data = await api.coachModelLogs(convId);
      setModelLogs(data.logs || []);
    } catch (e) {
      setModelLogs([{ id: 'error', task: 'error', model: '', response: e.message }]);
    } finally {
      setLogsLoading(false);
    }
  };

  const openInfo = async () => {
    setShowInfo(true);
    loadLogs();
  };

  if (authLoading || loading) return <div className="text-gray-500 text-center py-20">教练上线中...</div>;

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] sm:h-[calc(100vh-7rem)] max-w-2xl mx-auto">
      {/* 顶部栏 */}
      <div className="flex justify-between items-center gap-3 py-2">
        <div />
        <div className="flex items-center gap-2">
          <button
            onClick={openInfo}
            disabled={!convId}
            aria-label="对话信息"
            className="flex h-8 w-8 items-center justify-center rounded-full border border-gray-700 text-sm font-semibold text-gray-400 hover:border-gray-500 hover:text-gray-200 transition-colors disabled:opacity-40"
          >
            i
          </button>
        <button
          onClick={startNew}
          disabled={starting}
          className="text-xs text-gray-400 hover:text-gray-200 border border-gray-700 hover:border-gray-500 rounded-lg px-3 py-1.5 transition-colors disabled:opacity-50"
        >
          {starting ? '开启中...' : '+ 新对话'}
        </button>
        </div>
      </div>
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto space-y-4 py-4 pr-1">
        {messages.map((m, i) => (
          <MessageBubble key={i} role={m.role} content={m.content} avatarUrl={m.role === 'coach' ? avatarUrl : null} />
        ))}
        {sending && (
          <MessageBubble role="coach" content="..." typing avatarUrl={avatarUrl} />
        )}
        <div ref={bottomRef} />
      </div>

      {/* 输入区 */}
      <div className="py-3 flex gap-2 border-t border-gray-800">
        <input
          className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-gray-500"
          placeholder="跟教练说点什么..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
          disabled={sending}
        />
        <button
          onClick={send}
          disabled={sending || !input.trim()}
          className="px-4 py-3 rounded-xl bg-orange-500 hover:bg-orange-400 disabled:bg-gray-700 disabled:text-gray-500 text-white font-medium transition-colors text-sm"
        >
          发送
        </button>
      </div>

      {showInfo && (
        <ConversationInfoDrawer
          model={model}
          topics={topics}
          providerOrder={providerOrder}
          onProviderChange={updateProviderPreference}
          logs={modelLogs}
          loading={logsLoading}
          onRefresh={loadLogs}
          onClose={() => setShowInfo(false)}
        />
      )}
    </div>
  );
}

function ConversationInfoDrawer({
  model,
  topics,
  providerOrder,
  onProviderChange,
  logs,
  loading,
  onRefresh,
  onClose,
}) {
  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-xl border-l border-gray-800 bg-gray-950 shadow-2xl">
      <div className="flex items-center justify-between border-b border-gray-800 px-4 py-3">
        <div>
          <div className="text-sm font-semibold text-white">对话信息</div>
          <div className="text-xs text-gray-500">模型、话题与最近调用日志</div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onRefresh}
            className="rounded-lg border border-gray-700 px-2 py-1 text-xs text-gray-300 hover:border-gray-500"
          >
            刷新
          </button>
          <button
            onClick={onClose}
            className="rounded-lg border border-gray-700 px-2 py-1 text-xs text-gray-300 hover:border-gray-500"
          >
            关闭
          </button>
        </div>
      </div>
      <div className="h-[calc(100vh-3.5rem)] overflow-y-auto p-4 space-y-3">
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-3">
          <div className="mb-3 text-xs font-medium text-gray-500">模型设置</div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="text-xs text-gray-400">
              当前模型：<span className="text-gray-200">{model || '尚未调用'}</span>
            </div>
            <label className="flex items-center gap-2 text-xs text-gray-400">
              优先模型
              <select
                value={providerOrder[0] || 'gemini'}
                onChange={e => onProviderChange(e.target.value)}
                className="bg-gray-950 border border-gray-700 rounded-lg px-2 py-1 text-gray-300 focus:outline-none focus:border-gray-500"
              >
                <option value="gemini">Gemini</option>
                <option value="anthropic">Claude</option>
              </select>
            </label>
          </div>
        </div>

        <div className="rounded-xl border border-gray-800 bg-gray-900 p-3">
          <div className="mb-3 text-xs font-medium text-gray-500">当前话题</div>
          {topics.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {topics.map(topic => (
                <span key={topic} className="rounded-full border border-gray-700 bg-gray-950 px-2 py-0.5 text-xs text-gray-300">
                  {TOPIC_LABELS[topic] || topic}
                </span>
              ))}
            </div>
          ) : (
            <div className="text-xs text-gray-600">尚未识别</div>
          )}
        </div>

        <div className="pt-2 text-xs font-medium text-gray-500">模型调用日志</div>
        {loading && <div className="text-sm text-gray-500">读取中...</div>}
        {!loading && logs.length === 0 && <div className="text-sm text-gray-500">暂无日志</div>}
        {!loading && logs.map(log => (
          <details key={log.id} className="rounded-lg border border-gray-800 bg-gray-900 p-3" open={false}>
            <summary className="cursor-pointer text-sm text-gray-200">
              {log.task} · {log.model || 'unknown'} · {formatLogTime(log.created_at)}
            </summary>
            <div className="mt-3 space-y-3">
              {log.request && (
                <LogBlock title="Request" value={JSON.stringify(log.request, null, 2)} />
              )}
              <LogBlock title="Response" value={log.response || ''} />
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}

function LogBlock({ title, value }) {
  return (
    <div>
      <div className="mb-1 text-xs font-medium text-gray-500">{title}</div>
      <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-lg bg-gray-950 p-3 text-xs leading-relaxed text-gray-300">
        {value}
      </pre>
    </div>
  );
}

function formatLogTime(value) {
  if (!value) return '';
  try {
    return new Date(value).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function MessageBubble({ role, content, typing, avatarUrl }) {
  const isCoach = role === 'coach';
  return (
    <div className={`flex gap-3 ${isCoach ? '' : 'flex-row-reverse'}`}>
      {/* 头像 */}
      {isCoach && avatarUrl ? (
        <img src={avatarUrl} alt="coach" className="w-8 h-8 rounded-full flex-shrink-0 object-cover" />
      ) : (
        <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-sm font-bold ${
          isCoach ? 'bg-orange-500 text-white' : 'bg-gray-700 text-gray-300'
        }`}>
          {isCoach ? '🤖' : '我'}
        </div>
      )}
      {/* 气泡 */}
      <div className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
        isCoach
          ? 'bg-gray-800 text-gray-100 rounded-tl-sm'
          : 'bg-orange-500 text-white rounded-tr-sm'
      }`}>
        {typing ? (
          <span className="flex gap-1 items-center h-4">
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </span>
        ) : isCoach ? (
          <MarkdownMessage content={content} />
        ) : (
          <span className="whitespace-pre-wrap">{content}</span>
        )}
      </div>
    </div>
  );
}

function MarkdownMessage({ content }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => <p className="mb-2 last:mb-0 whitespace-pre-wrap">{children}</p>,
        strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
        em: ({ children }) => <em className="italic text-gray-100">{children}</em>,
        ul: ({ children }) => <ul className="my-2 ml-4 list-disc space-y-1">{children}</ul>,
        ol: ({ children }) => <ol className="my-2 ml-4 list-decimal space-y-1">{children}</ol>,
        li: ({ children }) => <li className="pl-1">{children}</li>,
        h1: ({ children }) => <h1 className="mb-2 text-base font-semibold text-white">{children}</h1>,
        h2: ({ children }) => <h2 className="mb-2 text-base font-semibold text-white">{children}</h2>,
        h3: ({ children }) => <h3 className="mb-2 text-sm font-semibold text-white">{children}</h3>,
        blockquote: ({ children }) => (
          <blockquote className="my-2 border-l-2 border-gray-500 pl-3 text-gray-300">
            {children}
          </blockquote>
        ),
        a: ({ children, href }) => (
          <a
            href={href}
            target="_blank"
            rel="noreferrer"
            className="text-orange-300 underline decoration-orange-300/60 underline-offset-2"
          >
            {children}
          </a>
        ),
        code: ({ children, className }) => {
          const inline = !className;
          if (inline) {
            return (
              <code className="rounded bg-gray-950/70 px-1 py-0.5 text-xs text-orange-200">
                {children}
              </code>
            );
          }
          return <code className={className}>{children}</code>;
        },
        pre: ({ children }) => (
          <pre className="my-2 overflow-x-auto rounded-lg bg-gray-950 p-3 text-xs leading-relaxed text-gray-200">
            {children}
          </pre>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
