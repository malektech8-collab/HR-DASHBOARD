import { useState, useEffect, lazy, Suspense } from 'react';
import { AppLayout } from './components/layout/AppLayout';
import { LoginGate } from './components/auth/LoginGate';
import { CommandCenter } from './pages/CommandCenter'; // Statically imported for immediate landing load
import { PageSkeleton } from './components/ui/PageSkeleton';
import { fetchRefreshStatus } from './lib/api';
import type { RefreshStatus } from './lib/types';

// Lazy-loaded domain pages
const ExecutiveSummary = lazy(() => import('./pages/ExecutiveSummary').then(m => ({ default: m.ExecutiveSummary })));
const DataQuality = lazy(() => import('./pages/DataQuality').then(m => ({ default: m.DataQuality })));
const Workforce = lazy(() => import('./pages/Workforce').then(m => ({ default: m.Workforce })));
const Payroll = lazy(() => import('./pages/Payroll').then(m => ({ default: m.Payroll })));
const Attendance = lazy(() => import('./pages/Attendance').then(m => ({ default: m.Attendance })));
const Compliance = lazy(() => import('./pages/Compliance').then(m => ({ default: m.Compliance })));
const EmployeeRelations = lazy(() => import('./pages/EmployeeRelations').then(m => ({ default: m.EmployeeRelations })));
const Recruitment = lazy(() => import('./pages/Recruitment').then(m => ({ default: m.Recruitment })));
const Talent = lazy(() => import('./pages/Talent').then(m => ({ default: m.Talent })));
const DataOnboarding = lazy(() => import('./pages/DataOnboarding').then(m => ({ default: m.DataOnboarding })));

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
        return <DataQuality onNavigate={setCurrentPage} />;
      case 'onboarding':
        return <DataOnboarding />;
      default:
        return <CommandCenter onNavigate={setCurrentPage} />;
    }
  };


  return (
    <LoginGate>
      <AppLayout
        currentPage={currentPage}
        onPageChange={setCurrentPage}
        reportMonth="2026-06"
        lastRefreshAt={metadata?.last_refresh_at || 'Unknown'}
        refreshStatus={syncStatus}
      >
        <Suspense fallback={<PageSkeleton />}>
          {renderPage()}
        </Suspense>
      </AppLayout>
    </LoginGate>
  );
}

export default App;
