import React, { useEffect, useState } from 'react';
import { fetchDataQualitySummary, fetchDataQualityExceptions } from '../lib/api';
import type { DataQualitySummaryData, DQExceptionItem } from '../lib/types';
import { ExceptionTable } from '../components/tables/ExceptionTable';
import { ShieldCheck, ShieldAlert, Users, FolderKanban, ShieldCheck as CC, Globe2, Copy, Wallet, CheckCircle } from 'lucide-react';

export const DataQuality: React.FC = () => {
  const [summary, setSummary] = useState<DataQualitySummaryData | null>(null);
  const [exceptions, setExceptions] = useState<DQExceptionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
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
    }
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

  // Get semantic color for DQ score
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

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Data Quality Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">Audit compliance status, database completeness tracker, and individual exceptions log.</p>
      </div>

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
              className={`bg-card border rounded-lg p-4 flex flex-col justify-between min-h-[110px] transition-all hover:bg-slate-900/10 ${
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
                  <span className="text-[9px] font-bold uppercase text-muted-foreground bg-slate-950/20 px-1 py-0.5 rounded border border-border">
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
    </div>
  );
};
