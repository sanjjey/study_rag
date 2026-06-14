import ReactMarkdown from 'react-markdown';
import { CheckCircle, Cpu, User } from 'lucide-react';

const FLAG_RE = /(\[VERIFIED\]|\[INFERRED\]|\[GENERAL\])/g;

function AnnotatedText({ text }) {
  const parts = text.split(FLAG_RE);
  return (
    <>
      {parts.map((part, i) => {
        if (part === '[VERIFIED]') return <span key={i} className="flag flag-verified">{part}</span>;
        if (part === '[INFERRED]') return <span key={i} className="flag flag-inferred">{part}</span>;
        if (part === '[GENERAL]') return <span key={i} className="flag flag-general">{part}</span>;
        return <ReactMarkdown key={i}>{part}</ReactMarkdown>;
      })}
    </>
  );
}

export default function MessageBubble({ msg, mode }) {
  const isUser = msg.role === 'user';
  const ts = msg.timestamp
    ? new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : null;

  return (
    <div className={`message ${isUser ? 'user' : 'ai'}`}>
      <div className="msg-header">
        <span className="msg-role">
          {isUser
            ? <><User size={14} /> You</>
            : <>{mode === 'rag' ? <CheckCircle size={14} color="var(--accent-green)" /> : <Cpu size={14} color="var(--secondary)" />} Academic AI</>
          }
        </span>
        {ts && <span className="msg-time">{ts}</span>}
      </div>

      <div className="msg-body">
        {isUser
          ? <p>{msg.content}</p>
          : <AnnotatedText text={msg.content} />
        }
      </div>

      {msg.sources && msg.sources.length > 0 && (
        <div className="msg-sources">
          <small>Sources: {msg.sources.map(s => s.name).join(' · ')}</small>
        </div>
      )}
    </div>
  );
}
