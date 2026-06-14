import { BookOpen, Brain, ClipboardCheck, Upload, FolderOpen, GraduationCap, LogOut, User } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const TABS = [
  { id: 'rag', label: 'RAG Chat', Icon: BookOpen },
  { id: 'hallucinate', label: 'Exploratory', Icon: Brain },
  { id: 'mock', label: 'Mock Test', Icon: ClipboardCheck },
  { id: 'documents', label: 'Documents', Icon: FolderOpen },
  { id: 'upload', label: 'Upload', Icon: Upload },
];

export default function Navbar({ activeTab, onTabChange }) {
  const { user, logout } = useAuth();

  return (
    <nav className="navbar">
      <div className="logo">
        <GraduationCap size={28} />
        <span>AcademicOS</span>
      </div>

      <div className="nav-links">
        {TABS.map(({ id, label, Icon }) => (
          <button
            key={id}
            className={`nav-link ${activeTab === id ? 'active' : ''}`}
            onClick={() => onTabChange(id)}
          >
            <Icon size={16} />
            <span>{label}</span>
          </button>
        ))}
      </div>

      <div className="nav-user">
        <User size={16} />
        <span>{user?.username}</span>
        <button className="btn-icon" onClick={logout} title="Sign out">
          <LogOut size={16} />
        </button>
      </div>
    </nav>
  );
}
