import { Send } from 'lucide-react';

export default function ChatInput({ value, onChange, onSend, loading, placeholder }) {
  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="chat-input-wrapper glass">
      <textarea
        className="chat-input"
        placeholder={placeholder || 'Ask a question…'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKey}
        disabled={loading}
        rows={3}
      />
      <button className="btn-send" onClick={onSend} disabled={loading || !value.trim()}>
        <Send size={18} />
      </button>
    </div>
  );
}
