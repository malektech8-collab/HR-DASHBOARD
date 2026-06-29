import { useState, useEffect } from 'react';
import { AppLayout } from './components/layout/AppLayout';
import { CommandCenter } from './pages/CommandCenter';
import { ExecutiveSummary } from './pages/ExecutiveSummary';
import { DataQuality } from './pages/DataQuality';
import { Workforce } from './pages/Workforce';
import { Payroll } from './pages/Payroll';
import { Attendance } from './pages/Attendance';
import { Compliance } from './pages/Compliance';
import { EmployeeRelations } from './pages/EmployeeRelations';
import { Recruitment } from './pages/Recruitment';
import { Talent } from './pages/Talent';
import { fetchRefreshStatus } from './lib/api';
import type { RefreshStatus } from './lib/types';

function App() {
  const [currentPage, setCurrentPage] = useState('command-center');
  const [metadata, setMetadata] = useState<RefreshStatus | null>(null);
  const [syncStatus, setSyncStatus] = useState<'success' | 'error' | 'refreshing'>('success');

  console.log("APP STATE - currentPage:", currentPage);

  // Load refresh status metadata from FastAPI
  useEffect(() => {
    async function loadMeta() {
      try {
        setSyncStatus('refreshing');
        const meta = await fetchRefreshStatus();
        setMetadata(meta);
        setSyncStatus(meta.status === 'success' ? 'success' : 'error');
      } catch (err) {
        console.error('Failed to load system metadata:', err);
        setSyncStatus('error');
      }
    }
    loadMeta();
  }, [currentPage]);

  // Page Switcher Logic
  const renderPage = () => {
    switch (currentPage) {
      case 'command-center':
        return <CommandCenter onNavigate={setCurrentPage} />;
      case 'executive':
        return <ExecutiveSummary onNavigate={setCurrentPage} />;
      case 'workforce':
        return <Workforce />;
      case 'payroll':
        return <Payroll />;
      case 'attendance':
        return <Attendance />;
      case 'compliance':
        return <Compliance />;
      case 'er':
        return <EmployeeRelations />;
      case 'recruitment':
        return <Recruitment />;
      case 'talent':
        return <Talent />;
      case 'data-quality':
        return <DataQuality />;
      default:
        return <CommandCenter onNavigate={setCurrentPage} />;
    }
  };


  return (
    <AppLayout
      currentPage={currentPage}
      onPageChange={setCurrentPage}
      reportMonth="2026-06"
      lastRefreshAt={metadata?.last_refresh_at || 'Unknown'}
      refreshStatus={syncStatus}
    >
      {renderPage()}
    </AppLayout>
  );
}

export default App;
