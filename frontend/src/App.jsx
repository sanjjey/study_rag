import { useState } from 'react';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ErrorBoundary } from './components/ErrorBoundary';
import LoginPage from './pages/LoginPage';
import Navbar from './components/Navbar';
import ChatWindow from './components/ChatWindow';
import MockTestPanel from './components/MockTestPanel';
import UploadPanel from './components/UploadPanel';
import DocumentManager from './components/DocumentManager';

function Shell() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('rag');
  const [docRefresh, setDocRefresh] = useState(0);

  if (!user) return <LoginPage />;

  return (
    <>
      <Navbar activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="container">
        {activeTab === 'rag' && <ChatWindow mode="rag" />}
        {activeTab === 'hallucinate' && <ChatWindow mode="hallucinate" />}
        {activeTab === 'mock' && <MockTestPanel />}
        {activeTab === 'upload' && (
          <UploadPanel onUploadSuccess={() => setDocRefresh(n => n + 1)} />
        )}
        {activeTab === 'documents' && (
          <DocumentManager refreshTrigger={docRefresh} />
        )}
      </main>
    </>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <Shell />
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: 'var(--bg-card)',
              color: 'var(--text-main)',
              border: '1px solid var(--border)',
              backdropFilter: 'blur(12px)',
            },
          }}
        />
      </AuthProvider>
    </ErrorBoundary>
  );
}
