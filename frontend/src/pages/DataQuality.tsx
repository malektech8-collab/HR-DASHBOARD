import React, { useEffect, useState } from 'react';
import { fetchDataQualitySummary, fetchDataQualityExceptions } from '../lib/api';
import type { DataQualitySummaryData, DQExceptionItem } from '../lib/types';
import { ExceptionTable } from '../components/tables/ExceptionTable';
import { 
  ShieldCheck, 
  ShieldAlert, 
  Users, 
  FolderKanban, 
  ShieldCheck as CC, 
  Globe2, 
  Copy, 
  Wallet, 
  CheckCircle,
  Download,
  UploadCloud,
  RefreshCw,
  Terminal,
  CheckCircle2,
  XCircle,
  AlertCircle
} from 'lucide-react';
import { useTemplatesQuery, useRefreshMutation } from '../hooks/useDataManagement';
import { getTemplateDownloadUrl } from '../lib/api';

interface DataQualityProps {
  /** Uploading moved to Data Onboarding; the page links there. */
  onNavigate?: (page: string) => void;
}

export const DataQuality: React.FC<DataQualityProps> = ({ onNavigate }) => {
  const [summary, setSummary] = useState<DataQualitySummaryData | null>(null);
  const [exceptions, setExceptions] = useState<DQExceptionItem[] | null>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Tab control state
  const [activeTab, setActiveTab] = useState<'audit' | 'management'>('audit');
  
  // Data management states

  // TanStack Query hooks
  const { data: templates, isLoading: templatesLoading } = useTemplatesQuery();
  const refreshMutation = useRefreshMutation();

  const loadData = async () => {
    try {
      setLoading(true);
      const [sumData, excData] = await Promise.all([
        fetchDataQualitySummary(),
        fetchDataQualityExceptions()
      ]);
      setSummary(sumData);
      setExceptions(excData.exceptions);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to fetch data quality records');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-3 text-muted-foreground">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
        <p className="text-sm font-semibold tracking-wide">Loading Data Quality Dashboard...</p>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="bg-critical/5 border border-critical/20 rounded-xl p-8 max-w-lg mx-auto text-center my-12 text-foreground">
        <ShieldAlert className="w-12 h-12 text-critical mx-auto mb-4 animate-pulse" />
        <h3 className="text-lg font-bold">API Connection Error</h3>
        <p className="text-sm text-muted-foreground mt-2">{error || 'Verify FastAPI backend server is running.'}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-6 px-4 py-2 bg-critical text-white rounded-lg font-semibold text-xs hover:bg-red-600 transition"
        >
          Try Again
        </button>
      </div>
    );
  }

  const isHealthy = summary.data_quality_score >= 95.0;
  const isWarning = summary.data_quality_score >= 90.0 && summary.data_quality_score < 95.0;

  const scoreColor = isHealthy 
    ? 'text-healthy bg-healthy/5 border-healthy/30' 
    : isWarning 
      ? 'text-warning bg-warning/5 border-warning/30' 
      : 'text-critical bg-critical/5 border-critical/30';

  const metrics = [
    { label: 'Missing Manager', value: summary.missing_manager_count, icon: Users, isCritical: false },
    { label: 'Missing Project', value: summary.missing_project_count, icon: FolderKanban, isCritical: false },
    { label: 'Missing Cost Center', value: summary.missing_cost_center_count, icon: CC, isCritical: false },
    { label: 'Missing Nationality', value: summary.missing_nationality_count, icon: Globe2, isCritical: false },
    { label: 'Duplicate Employee ID', value: summary.duplicate_employee_count, icon: Copy, isCritical: true },
    { label: 'Invalid Payroll Record', value: summary.invalid_payroll_count, icon: Wallet, isCritical: true },
  ];

  const handleRefreshTrigger = () => {
    refreshMutation.mutate(undefined, {
      onSuccess: (data) => {
        if (data.status === 'success') {
          // Re-load original data values immediately after successfully rebuilding
          loadData();
        }
      }
    });
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Data Quality Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1">Audit compliance status, database completeness tracker, and individual exceptions log.</p>
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="flex border-b border-border gap-6">
        <button
          onClick={() => setActiveTab('audit')}
          className={`pb-3 text-sm font-semibold tracking-wide border-b-2 transition-all duration-200 ${
            activeTab === 'audit'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          Audit Report
        </button>
        <button
          onClick={() => setActiveTab('management')}
          className={`pb-3 text-sm font-semibold tracking-wide border-b-2 transition-all duration-200 ${
            activeTab === 'management'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          Local Data Management
        </button>
      </div>

      {activeTab === 'audit' ? (
        <>
          {/* Main Score Banner */}
          <div className={`border rounded-xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-6 ${scoreColor}`}>
            <div className="flex items-center gap-4">
              {isHealthy ? (
                <ShieldCheck className="w-12 h-12 text-healthy flex-shrink-0" />
              ) : (
                <ShieldAlert className="w-12 h-12 flex-shrink-0" />
              )}
              <div>
                <h2 className="text-lg font-bold text-foreground">Data Quality Score</h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  The overall database completeness score calculated across all active employee fields. Target is &gt;95%.
                </p>
              </div>
            </div>
            <div className="text-center md:text-right">
              <span className="text-4xl font-extrabold tracking-tight block text-foreground">
                {summary.data_quality_score}%
              </span>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider inline-block mt-1 ${
                isHealthy ? 'bg-healthy/10 text-healthy' : isWarning ? 'bg-warning/10 text-warning' : 'bg-critical/10 text-critical'
              }`}>
                {isHealthy ? 'Compliant' : isWarning ? 'Needs Attention' : 'Critical Risk'}
              </span>
            </div>
          </div>

          {/* Counts Grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {metrics.map((m, idx) => {
              const Icon = m.icon;
              const hasIssues = m.value > 0;
              return (
                <div 
                  key={idx} 
                  className={`bg-card border rounded-lg p-4 flex flex-col justify-between min-h-[110px] transition-all hover:bg-muted/40 ${
                    hasIssues 
                      ? m.isCritical 
                        ? 'border-critical/30 shadow-critical/5' 
                        : 'border-warning/30 shadow-warning/5'
                      : 'border-border'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{m.label}</span>
                    <Icon className={`w-3.5 h-3.5 ${hasIssues ? (m.isCritical ? 'text-critical' : 'text-warning') : 'text-muted-foreground'}`} />
                  </div>
                  <div className="mt-3 flex items-baseline justify-between">
                    <span className={`text-xl font-bold ${hasIssues ? (m.isCritical ? 'text-critical' : 'text-warning') : 'text-foreground'}`}>
                      {m.value}
                    </span>
                    {hasIssues ? (
                      <span className="text-[9px] font-bold uppercase text-muted-foreground bg-muted px-1 py-0.5 rounded border border-border">
                        Audit
                      </span>
                    ) : (
                      <CheckCircle className="w-3.5 h-3.5 text-healthy" />
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Exception Table Section */}
          <div className="space-y-4">
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-foreground">Exceptions Logs</h2>
              <p className="text-xs text-muted-foreground mt-0.5">Filter, sort, and search the comprehensive register of database validation failures.</p>
            </div>
            <ExceptionTable data={exceptions} />
          </div>
        </>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Columns - Templates and Upload */}
          <div className="lg:col-span-2 space-y-8">
            {/* Template Downloader Section */}
            <div className="bg-card border border-border rounded-xl p-6 space-y-4">
              <div>
                <h3 className="text-lg font-bold flex items-center gap-2">
                  <Download className="w-5 h-5 text-primary" /> Download Data Schema Templates
                </h3>
                <p className="text-xs text-muted-foreground mt-1">Get CSV template files formatted correctly to match database fields.</p>
              </div>
              
              {templatesLoading ? (
                <div className="text-xs text-muted-foreground">Loading templates list...</div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {templates?.map((t) => (
                    <div key={t.name} className="border border-border bg-muted/40 rounded-lg p-4 flex flex-col justify-between hover:bg-muted/60 transition">
                      <div className="space-y-1">
                        <p className="text-sm font-bold capitalize">{t.name.replace("_", " ")}</p>
                        <p className="text-xs text-muted-foreground line-clamp-2">{t.description}</p>
                      </div>
                      <a
                        href={getTemplateDownloadUrl(t.name)}
                        className="mt-4 flex items-center justify-center gap-2 px-3 py-1.5 bg-muted hover:bg-secondary text-foreground text-xs font-semibold rounded-lg transition border border-border"
                        download={t.filename}
                      >
                        <Download className="w-3.5 h-3.5" /> Download Schema Template
                      </a>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Upload moved to Data Onboarding (upload UI cycle).
                What used to be here wrote a renamed file straight into
                data/silver with no validation, no preview and no coverage
                declaration - the P0-2 defect. Pointing at the real flow rather
                than keeping a second one. */}
            <div className="bg-card border border-border rounded-xl p-6 space-y-4">
              <div>
                <h3 className="text-lg font-bold flex items-center gap-2">
                  <UploadCloud className="w-5 h-5 text-primary" /> Uploading data
                </h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Uploads now go through <span className="font-semibold text-foreground">Data Onboarding</span>,
                  where the file is checked against its contract and previewed before anything is committed.
                </p>
              </div>
              <button
                onClick={() => onNavigate?.('onboarding')}
                className="px-4 py-2 bg-primary text-primary-foreground text-xs font-semibold rounded-lg hover:opacity-90"
              >
                Go to Data Onboarding
              </button>
            </div>
          </div>

          {/* Right Column - Rebuild & Console Logs */}
          <div className="space-y-8">
            <div className="bg-card border border-border rounded-xl p-6 space-y-6">
              <div>
                <h3 className="text-lg font-bold flex items-center gap-2">
                  <RefreshCw className="w-5 h-5 text-primary" /> Warehouse Pipeline Control
                </h3>
                <p className="text-xs text-muted-foreground mt-1">Force a full downstream analytical metrics rebuild. Runs synthetics data check, ingestion, schemas validation, and dbt warehouse tables construction.</p>
              </div>

              <button
                onClick={handleRefreshTrigger}
                disabled={refreshMutation.isPending}
                className="w-full flex items-center justify-center gap-2 py-3 bg-primary text-primary-foreground font-semibold text-sm rounded-lg hover:opacity-90 transition disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${refreshMutation.isPending ? 'animate-spin' : ''}`} />
                {refreshMutation.isPending ? "Rebuilding Analytics Warehouse..." : "Rebuild & Refresh Warehouse"}
              </button>

              {refreshMutation.isSuccess && refreshMutation.data.status === 'success' && (
                <div className="bg-healthy/10 border border-healthy/30 text-healthy px-4 py-3 rounded-lg flex items-center gap-3 text-xs">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                  <div>
                    <span className="font-bold">Pipeline Healthy: </span>
                    All analytical views rebuilt and TanStack queries invalidated. UI updated with fresh metrics.
                  </div>
                </div>
              )}

              {refreshMutation.isSuccess && refreshMutation.data.status === 'failed' && (
                <div className="bg-critical/10 border border-critical/30 text-critical px-4 py-3 rounded-lg flex items-center gap-3 text-xs">
                  <XCircle className="w-4 h-4 flex-shrink-0" />
                  <div>
                    <span className="font-bold">Pipeline Failed: </span>
                    Subprocess execution returned error code {refreshMutation.data.return_code}. Inspect terminal logs below.
                  </div>
                </div>
              )}

              {refreshMutation.isError && (
                <div className="bg-critical/10 border border-critical/30 text-critical px-4 py-3 rounded-lg flex items-center gap-3 text-xs">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <div>
                    <span className="font-bold">Request Error: </span>
                    {refreshMutation.error.message || "Failed to contact pipeline refresh endpoint."}
                  </div>
                </div>
              )}

              {/* Execution time if refresh run completed */}
              {refreshMutation.isSuccess && (
                <div className="text-[10px] text-muted-foreground flex justify-between">
                  <span>Execution Time: {refreshMutation.data.execution_time_seconds}s</span>
                  <span>Exit Code: {refreshMutation.data.return_code}</span>
                </div>
              )}
            </div>

            {/* Subprocess console logs console panel */}
            <div className="bg-card border border-border rounded-xl p-6 space-y-4">
              <h3 className="text-sm font-bold uppercase tracking-wider flex items-center gap-2">
                <Terminal className="w-4 h-4 text-primary" /> Execution Console Logs
              </h3>
              
              <div className="bg-black text-green-400 p-4 rounded-lg font-mono text-xs overflow-auto max-h-[300px] border border-border shadow-inner">
                {refreshMutation.isPending && (
                  <div className="animate-pulse">
                    <span className="text-blue-400">&gt;</span> Initializing python subprocess...
                    <br />
                    <span className="text-blue-400">&gt;</span> Running sys.executable scripts/refresh_all.py
                    <br />
                    <span className="text-yellow-400">Executing dbt run & tests... Please wait.</span>
                  </div>
                )}
                {refreshMutation.isIdle && (
                  <span className="text-muted-foreground">No active execution logs. Click "Rebuild & Refresh" above to run pipeline.</span>
                )}
                {refreshMutation.isSuccess && (
                  <div>
                    {refreshMutation.data.stdout && (
                      <div>
                        <span className="text-blue-400 font-bold">--- STDOUT ---</span>
                        <pre className="whitespace-pre-wrap mt-1">{refreshMutation.data.stdout}</pre>
                      </div>
                    )}
                    {refreshMutation.data.stderr && (
                      <div className="mt-4">
                        <span className="text-red-400 font-bold">--- STDERR ---</span>
                        <pre className="whitespace-pre-wrap mt-1 text-red-300">{refreshMutation.data.stderr}</pre>
                      </div>
                    )}
                  </div>
                )}
                {refreshMutation.isError && (
                  <span className="text-red-400">Connection error: {refreshMutation.error.message}</span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
