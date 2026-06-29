import React, { useEffect, useState } from 'react';
import { fetchExecutiveSummary, fetchDataQualityExceptions } from '../lib/api';
import type { ExecutiveSummaryData, DQExceptionItem } from '../lib/types';
import { KpiCard } from '../components/cards/KpiCard';
import { LineChartCard } from '../components/charts/LineChartCard';
import { BarChartCard } from '../components/charts/BarChartCard';
import { formatCurrency, formatNumber } from '../lib/formatters';
import { AlertCircle, ArrowRight, ShieldAlert, Sparkles } from 'lucide-react';

interface ExecutiveSummaryProps {
  onNavigate: (page: string) => void;
}

export const ExecutiveSummary: React.FC<ExecutiveSummaryProps> = ({ onNavigate }) => {
  const [data, setData] = useState<ExecutiveSummaryData | null>(null);
  const [exceptions, setExceptions] = useState<DQExceptionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [sumData, excData] = await Promise.all([
          fetchExecutiveSummary(),
          fetchDataQualityExceptions()
        ]);
        setData(sumData);
        setExceptions(excData.exceptions);
      } catch (err: any) {
        console.error(err);
        setError(err.message || 'Failed to fetch executive dashboard data');
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
        <p className="text-sm font-semibold tracking-wide">Loading Executive Dashboard...</p>
      </div>
    );
  }

  if (error || !data) {
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

  // Find overall data quality KPI to show warning
  const dqKpi = data.kpis.find(k => k.key === 'data_quality_score');
  const isDqLow = dqKpi && dqKpi.value < 95.0;

  // Filter top 3 exceptions requiring action (Critical severity first)
  const exceptionsRequiringAction = [...exceptions]
    .sort((a, b) => {
      if (a.severity.toLowerCase() === 'critical' && b.severity.toLowerCase() !== 'critical') return -1;
      if (a.severity.toLowerCase() !== 'critical' && b.severity.toLowerCase() === 'critical') return 1;
      return 0;
    })
    .slice(0, 3);

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            Executive Summary
            <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-primary/10 border border-primary/20 text-primary font-bold uppercase tracking-wider">
              <Sparkles className="w-3 h-3 animate-spin" /> Live Metrics
            </span>
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Workforce sizes, total payroll, overtime cost, and data quality overview.</p>
        </div>
      </div>

      {/* Data Quality Banner (if low score) */}
      {isDqLow && (
        <div className="bg-warning/5 border border-warning/20 rounded-xl p-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-warning flex-shrink-0" />
            <div>
              <p className="text-sm font-semibold text-foreground">Data Quality Issues Detected</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                The overall data quality score is currently <span className="font-semibold text-warning">{dqKpi.value}%</span>, which is below the 95% target threshold. Report values may contain discrepancies.
              </p>
            </div>
          </div>
          <button
            onClick={() => onNavigate('data-quality')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-warning/10 hover:bg-warning/20 text-warning text-xs font-semibold transition"
          >
            Review Issues <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {data.kpis.map((kpi) => (
          <KpiCard
            key={kpi.key}
            label={kpi.label}
            value={kpi.value}
            unit={kpi.unit}
            trendValue={kpi.trend_value}
            trendDirection={kpi.trend_direction}
            status={kpi.status}
          />
        ))}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LineChartCard
          title="Workforce Headcount Trend"
          xAxisData={data.charts.months}
          seriesData={data.charts.headcount_trend}
          seriesName="Active Headcount"
          color="#38bdf8"
          valueFormatter={(val) => `${formatNumber(val)} employees`}
        />
        <BarChartCard
          title="Monthly Payroll Cost Trend"
          xAxisData={data.charts.months}
          seriesData={data.charts.payroll_trend}
          seriesName="Payroll Cost"
          color="#6366f1"
          valueFormatter={formatCurrency}
        />
      </div>

      {/* Actionable Exceptions List */}
      <div className="bg-card border border-border rounded-xl p-6 shadow-lg space-y-4">
        <div className="flex items-center justify-between border-b border-border/50 pb-3">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-foreground">Exceptions Requiring Action</h2>
            <p className="text-xs text-muted-foreground mt-0.5">Top critical data issues identified in the employee database that require prompt correction.</p>
          </div>
          <button 
            onClick={() => onNavigate('data-quality')}
            className="text-xs text-primary hover:text-sky-300 font-semibold transition flex items-center gap-1"
          >
            View All Exceptions <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="divide-y divide-border/30">
          {exceptionsRequiringAction.length > 0 ? (
            exceptionsRequiringAction.map((exc, idx) => (
              <div key={idx} className="py-3 first:pt-0 last:pb-0 flex flex-col md:flex-row md:items-center justify-between gap-3 text-sm">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-muted-foreground">{exc.employee_id || 'SYSTEM'}</span>
                    <span className="font-semibold text-foreground">{exc.employee_name}</span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${
                      exc.severity.toLowerCase() === 'critical' ? 'bg-critical/10 text-critical' : 'bg-warning/10 text-warning'
                    }`}>
                      {exc.severity}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">{exc.description}</p>
                </div>
                <div className="md:text-right">
                  <span className="inline-block text-xs font-semibold px-2.5 py-1 rounded bg-primary/5 text-primary border border-primary/20">
                    Action: {exc.recommended_action}
                  </span>
                </div>
              </div>
            ))
          ) : (
            <p className="text-xs text-muted-foreground text-center py-4">No validation exceptions requiring review.</p>
          )}
        </div>
      </div>
    </div>
  );
};
