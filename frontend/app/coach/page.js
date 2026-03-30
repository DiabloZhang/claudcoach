'use client';
import { useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';

const USER_ID = 1;

export default function CoachPage() {
  const [convId, setConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [done, setDone] = useState(false);
  const [model, setModel] = useState(null);
  const [starting, setStarting] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    api.coachOpen(USER_ID).then(data => {
      setConvId(data.conversation_id);
      setMessages(data.messages);
      setDone(data.status === 'complete');
      if (data.model) setModel(data.model);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || sending || done) return;
    setInput('');
    setSending(true);
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    try {
      const res = await api.coachMessage(convId, text);
      setMessages(prev => [...prev, { role: 'coach', content: res.reply }]);
      if (res.model) setModel(res.model);
      if (res.is_complete) setDone(true);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'coach', content: `出错了：${e.message}` }]);
    } finally {
      setSending(false);
    }
  };

  const startNew = async () => {
    setStarting(true);
    try {
      const data = await api.coachNew(USER_ID);
      setConvId(data.conversation_id);
      setMessages(data.messages);
      setDone(false);
      if (data.model) setModel(data.model);
    } catch (e) {
      alert('开启新对话失败：' + e.message);
    } finally {
      setStarting(false);
    }
  };

  if (loading) return <div className="text-gray-500 text-center py-20">教练上线中...</div>;

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] sm:h-[calc(100vh-7rem)] max-w-2xl mx-auto">
      {/* 顶部栏 */}
      <div className="flex justify-end py-2">
        <button
          onClick={startNew}
          disabled={starting}
          className="text-xs text-gray-400 hover:text-gray-200 border border-gray-700 hover:border-gray-500 rounded-lg px-3 py-1.5 transition-colors disabled:opacity-50"
        >
          {starting ? '开启中...' : '+ 新对话'}
        </button>
      </div>
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto space-y-4 py-4 pr-1">
        {messages.map((m, i) => (
          <MessageBubble key={i} role={m.role} content={m.content} />
        ))}
        {sending && (
          <MessageBubble role="coach" content="..." typing />
        )}
        <div ref={bottomRef} />
      </div>

      {/* 模型指示器 */}
      {model && (
        <div className="flex justify-end pb-1">
          <span className="text-xs text-gray-600 bg-gray-800/50 px-2 py-0.5 rounded-full">
            {model}
          </span>
        </div>
      )}

      {/* 输入区 */}
      {done ? (
        <div className="py-4 text-center text-gray-500 text-sm">本次对话已结束</div>
      ) : (
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
      )}
    </div>
  );
}

function MessageBubble({ role, content, typing }) {
  const isCoach = role === 'coach';
  return (
    <div className={`flex gap-3 ${isCoach ? '' : 'flex-row-reverse'}`}>
      {/* 头像 */}
      <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-sm font-bold ${
        isCoach ? 'bg-orange-500 text-white' : 'bg-gray-700 text-gray-300'
      }`}>
        {isCoach ? '🤖' : '我'}
      </div>
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
        ) : <span className="whitespace-pre-wrap">{content}</span>}
      </div>
    </div>
  );
}
