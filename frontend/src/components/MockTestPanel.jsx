import { useState } from 'react';
import { ClipboardCheck, RefreshCw, Send } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import api from '../api/client';
import toast from 'react-hot-toast';

const SUBJECTS = ['General', 'Mathematics', 'Physics', 'Chemistry', 'Biology', 'Computer Science', 'History', 'Literature', 'Economics', 'Other'];
const DIFFICULTIES = ['Easy', 'Medium', 'Hard', 'Mixed'];
const QUESTION_TYPES = ['Short Answer', 'MCQ', 'True/False', 'Essay', 'Short Answer, MCQ'];

function ScoreBadge({ text }) {
  const match = text.match(/(\d+(\.\d+)?)\s*\/\s*10/);
  if (!match) return null;
  const score = parseFloat(match[1]);
  const color = score >= 8 ? 'var(--accent-green)' : score >= 5 ? 'var(--accent-yellow)' : 'var(--accent-red)';
  return (
    <div className="score-badge" style={{ borderColor: color, color }}>
      <span className="score-number">{score}</span>
      <span className="score-denom">/10</span>
    </div>
  );
}

export default function MockTestPanel() {
  const [config, setConfig] = useState({
    subject: 'General',
    difficulty: 'Medium',
    types: 'Short Answer, MCQ',
    num_questions: 5,
  });
  const [test, setTest] = useState(null);
  const [answer, setAnswer] = useState('');
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);

  const generateTest = async () => {
    setLoading(true);
    setTest(null);
    setEvaluation(null);
    setAnswer('');
    try {
      const { data } = await api.post('/mock-test/generate', config);
      setTest(data.test);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to generate test';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const evaluate = async () => {
    if (!answer.trim()) { toast.error('Write your answers before submitting'); return; }
    setEvaluating(true);
    try {
      const { data } = await api.post('/mock-test/evaluate', {
        query: `Mock test on ${config.subject} (${config.difficulty})`,
        student_answer: answer,
      });
      setEvaluation(data.evaluation);
    } catch {
      toast.error('Evaluation failed');
    } finally {
      setEvaluating(false);
    }
  };

  return (
    <div className="mock-panel">
      {/* Config */}
      <div className="mock-config glass">
        <h2>Mock Test Generator</h2>
        <div className="mock-config-grid">
          <div className="form-group">
            <label>Subject</label>
            <select className="form-input" value={config.subject} onChange={e => setConfig(c => ({ ...c, subject: e.target.value }))}>
              {SUBJECTS.map(s => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Difficulty</label>
            <select className="form-input" value={config.difficulty} onChange={e => setConfig(c => ({ ...c, difficulty: e.target.value }))}>
              {DIFFICULTIES.map(d => <option key={d}>{d}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Question Types</label>
            <select className="form-input" value={config.types} onChange={e => setConfig(c => ({ ...c, types: e.target.value }))}>
              {QUESTION_TYPES.map(t => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Questions ({config.num_questions})</label>
            <input
              type="range" min={1} max={15} value={config.num_questions}
              onChange={e => setConfig(c => ({ ...c, num_questions: Number(e.target.value) }))}
              className="range-input"
            />
          </div>
        </div>
        <button className="btn btn-primary" onClick={generateTest} disabled={loading}>
          {loading ? <><RefreshCw size={16} className="spin" /> Generating…</> : <><ClipboardCheck size={16} /> Generate Test</>}
        </button>
      </div>

      {/* Test */}
      {test && (
        <div className="mock-test glass">
          <h3>Practice Questions — {config.subject} · {config.difficulty}</h3>
          <div className="test-content">
            <ReactMarkdown>{test}</ReactMarkdown>
          </div>

          <div className="answer-section">
            <h4>Your Answers</h4>
            <textarea
              className="chat-input"
              style={{ minHeight: '160px' }}
              value={answer}
              onChange={e => setAnswer(e.target.value)}
              placeholder="Type your answers here. Reference questions by number (Q1, Q2, …)"
            />
            <button className="btn btn-primary" onClick={evaluate} disabled={evaluating}>
              {evaluating ? <><RefreshCw size={16} className="spin" /> Grading…</> : <><Send size={16} /> Submit for Grading</>}
            </button>
          </div>
        </div>
      )}

      {/* Evaluation */}
      {evaluation && (
        <div className="evaluation glass">
          <div className="eval-header">
            <h3>Evaluation Report</h3>
            <ScoreBadge text={evaluation} />
          </div>
          <div className="eval-content">
            <ReactMarkdown>{evaluation}</ReactMarkdown>
          </div>
          <button className="btn btn-secondary" onClick={generateTest} disabled={loading}>
            <RefreshCw size={16} /> Try Another Test
          </button>
        </div>
      )}
    </div>
  );
}
