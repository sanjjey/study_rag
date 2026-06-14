import { useEffect, useRef, useState } from 'react';
import { Trash2, Download, BookOpen, Brain } from 'lucide-react';
import MessageBubble from './MessageBubble';
import ChatInput from './ChatInput';
import api from '../api/client';
import toast from 'react-hot-toast';

const SUBJECTS = ['General', 'Mathematics', 'Physics', 'Chemistry', 'Biology', 'Computer Science', 'History', 'Literature', 'Economics', 'Other'];

export default function ChatWindow({ mode }) {
  const [messages, setMessages] = useState([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [subject, setSubject] = useState('General');
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async () => {
    if (!query.trim() || loading) return;

    const userMsg = { role: 'user', content: query, timestamp: Date.now() };
    setMessages(prev => [...prev, userMsg]);
    setQuery('');
    setLoading(true);

    try {
      const endpoint = mode === 'rag' ? '/chat/rag' : '/chat/hallucinate';
      const payload = { query: userMsg.content, subject: subject !== 'General' ? subject : undefined };
      const { data } = await api.post(endpoint, payload);

      setMessages(prev => [...prev, {
        role: 'ai',
        content: data.answer,
        sources: data.sources || [],
        timestamp: Date.now(),
      }]);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Backend error. Please try again.';
      toast.error(msg);
      setMessages(prev => [...prev, { role: 'ai', content: `**Error:** ${msg}`, timestamp: Date.now() }]);
    } finally {
      setLoading(false);
    }
  };

  const exportChat = () => {
    if (!messages.length) return;
    const lines = messages.map(m => `**${m.role === 'user' ? 'You' : 'AI'}:** ${m.content}`);
    const blob = new Blob([lines.join('\n\n')], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Chat exported');
  };

  const placeholder = mode === 'rag'
    ? 'Ask anything grounded in your uploaded notes…'
    : 'Explore any academic topic freely…';

  const modeLabel = mode === 'rag'
    ? { icon: <BookOpen size={14} />, text: 'RAG — answers grounded in your documents' }
    : { icon: <Brain size={14} />, text: 'Exploratory — uses broad AI knowledge' };

  return (
    <div className="chat-panel">
      <div className="chat-toolbar">
        <div className="mode-badge">
          {modeLabel.icon}
          <span>{modeLabel.text}</span>
        </div>
        <div className="toolbar-right">
          <select className="subject-select" value={subject} onChange={e => setSubject(e.target.value)}>
            {SUBJECTS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <button className="btn-icon" onClick={exportChat} title="Export chat" disabled={!messages.length}>
            <Download size={16} />
          </button>
          <button className="btn-icon" onClick={() => setMessages([])} title="Clear chat" disabled={!messages.length}>
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      <div className="chat-window">
        {messages.length === 0 && (
          <div className="chat-empty">
            {mode === 'rag'
              ? 'Upload documents then ask questions grounded in your study material.'
              : 'Ask any academic question — the AI will draw on its broad knowledge.'}
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} msg={msg} mode={mode} />
        ))}
        {loading && (
          <div className="message ai thinking">
            <span className="dot" /><span className="dot" /><span className="dot" />
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <ChatInput
        value={query}
        onChange={setQuery}
        onSend={handleSend}
        loading={loading}
        placeholder={placeholder}
      />
    </div>
  );
}
