import { useEffect, useState } from 'react';
import { FileText, Trash2, RefreshCw, AlertCircle } from 'lucide-react';
import api from '../api/client';
import toast from 'react-hot-toast';

export default function DocumentManager({ refreshTrigger }) {
  const [docs, setDocs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState(null);

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const [docsRes, statsRes] = await Promise.all([
        api.get('/documents'),
        api.get('/documents/stats'),
      ]);
      setDocs(docsRes.data.documents);
      setStats(statsRes.data);
    } catch {
      toast.error('Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs(); // eslint-disable-line react-hooks/set-state-in-effect
  }, [refreshTrigger]);

  const deleteDoc = async (bookName) => {
    if (!confirm(`Delete "${bookName}" and all its indexed content?`)) return;
    setDeleting(bookName);
    try {
      const { data } = await api.delete('/documents', { data: { book_name: bookName } });
      toast.success(`Deleted ${data.chunks_removed} chunks from "${bookName}"`);
      setDocs(prev => prev.filter(d => d.book_name !== bookName));
      setStats(prev => prev ? { ...prev, total_documents: prev.total_documents - 1 } : prev);
    } catch {
      toast.error('Delete failed');
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="doc-manager glass">
      <div className="doc-header">
        <h2>Document Library</h2>
        <button className="btn-icon" onClick={fetchDocs} disabled={loading} title="Refresh">
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
        </button>
      </div>

      {stats && (
        <div className="stats-bar">
          <div className="stat-chip"><span>{stats.total_documents}</span><small>Documents</small></div>
          <div className="stat-chip"><span>{stats.total_chunks}</span><small>Chunks</small></div>
          <div className="stat-chip"><span>{stats.subjects?.length || 0}</span><small>Subjects</small></div>
        </div>
      )}

      {!loading && docs.length === 0 && (
        <div className="empty-state">
          <AlertCircle size={36} />
          <p>No documents uploaded yet. Go to the Upload tab to get started.</p>
        </div>
      )}

      <ul className="doc-list">
        {docs.map((doc) => (
          <li key={doc.book_name} className="doc-item">
            <FileText size={20} />
            <div className="doc-info">
              <span className="doc-name">{doc.original_filename || doc.book_name}</span>
              <div className="doc-meta">
                {doc.subject && <span className="badge badge-info">{doc.subject}</span>}
                {doc.chapter && <span className="badge badge-default">{doc.chapter}</span>}
                <span className="badge badge-default">{doc.chunk_count} chunks</span>
              </div>
            </div>
            <button
              className="btn-icon danger"
              onClick={() => deleteDoc(doc.book_name)}
              disabled={deleting === doc.book_name}
              title="Delete document"
            >
              <Trash2 size={16} />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
