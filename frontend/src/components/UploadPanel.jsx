import { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, X } from 'lucide-react';
import api from '../api/client';
import toast from 'react-hot-toast';

const SUBJECTS = ['General', 'Mathematics', 'Physics', 'Chemistry', 'Biology', 'Computer Science', 'History', 'Literature', 'Economics', 'Other'];
const ACCEPTED = '.pdf,.pptx,.docx,.txt';

export default function UploadPanel({ onUploadSuccess }) {
  const [files, setFiles] = useState([]);
  const [subject, setSubject] = useState('General');
  const [chapter, setChapter] = useState('');
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const inputRef = useRef(null);

  const handleFiles = (selected) => {
    const list = Array.from(selected).map(f => ({
      file: f,
      status: 'pending',
      error: null,
    }));
    setFiles(list);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    handleFiles(e.dataTransfer.files);
  };

  const uploadAll = async () => {
    if (!files.length || uploading) return;
    setUploading(true);
    setProgress(0);

    const results = [];
    for (let i = 0; i < files.length; i++) {
      const entry = files[i];
      setFiles(prev => prev.map((f, idx) => idx === i ? { ...f, status: 'uploading' } : f));

      try {
        const form = new FormData();
        form.append('file', entry.file);
        form.append('subject', subject);
        form.append('chapter', chapter);

        const { data } = await api.post('/upload', form, {
          onUploadProgress: (e) => {
            setProgress(Math.round((e.loaded / e.total) * 100));
          },
        });

        setFiles(prev => prev.map((f, idx) =>
          idx === i ? { ...f, status: 'done', message: `${data.chunks_created} chunks indexed` } : f
        ));
        results.push({ success: true, name: entry.file.name, chunks: data.chunks_created });
      } catch (err) {
        const msg = err.response?.data?.detail || 'Upload failed';
        setFiles(prev => prev.map((f, idx) => idx === i ? { ...f, status: 'error', error: msg } : f));
        results.push({ success: false, name: entry.file.name });
      }
    }

    const ok = results.filter(r => r.success).length;
    if (ok) {
      toast.success(`${ok} file${ok > 1 ? 's' : ''} uploaded successfully`);
      onUploadSuccess?.();
    }
    setUploading(false);
  };

  const removeFile = (i) => setFiles(prev => prev.filter((_, idx) => idx !== i));

  return (
    <div className="upload-panel glass">
      <h2>Upload Study Materials</h2>
      <p className="text-muted">Supports PDF, PPTX, DOCX, TXT — up to 20 MB each</p>

      <div className="upload-meta">
        <div className="form-group">
          <label>Subject</label>
          <select className="form-input" value={subject} onChange={e => setSubject(e.target.value)}>
            {SUBJECTS.map(s => <option key={s}>{s}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label>Chapter / Topic (optional)</label>
          <input
            type="text"
            className="form-input"
            placeholder="e.g. Chapter 3: Thermodynamics"
            value={chapter}
            onChange={e => setChapter(e.target.value)}
          />
        </div>
      </div>

      <div
        className="drop-zone"
        onDragOver={e => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => !uploading && inputRef.current?.click()}
      >
        <Upload size={36} />
        <p>Drag & drop files here or <span className="link">browse</span></p>
        <small>{ACCEPTED.split(',').join(', ')}</small>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED}
          hidden
          onChange={e => handleFiles(e.target.files)}
        />
      </div>

      {files.length > 0 && (
        <ul className="file-list">
          {files.map((entry, i) => (
            <li key={i} className="file-item">
              <FileText size={16} />
              <span className="file-name">{entry.file.name}</span>
              <span className="file-size">{(entry.file.size / 1024).toFixed(0)} KB</span>
              {entry.status === 'pending' && (
                <button className="btn-icon" onClick={() => removeFile(i)}><X size={14} /></button>
              )}
              {entry.status === 'uploading' && <span className="badge badge-info">Uploading…</span>}
              {entry.status === 'done' && <span className="badge badge-success"><CheckCircle size={12} /> {entry.message}</span>}
              {entry.status === 'error' && <span className="badge badge-error"><AlertCircle size={12} /> {entry.error}</span>}
            </li>
          ))}
        </ul>
      )}

      {uploading && (
        <div className="progress-bar-wrapper">
          <div className="progress-bar" style={{ width: `${progress}%` }} />
          <span>{progress}%</span>
        </div>
      )}

      <button
        className="btn btn-primary"
        onClick={uploadAll}
        disabled={!files.length || uploading}
      >
        <Upload size={16} />
        {uploading ? 'Uploading…' : `Upload ${files.length} File${files.length !== 1 ? 's' : ''}`}
      </button>
    </div>
  );
}
