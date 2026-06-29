import React, { useEffect, useState } from 'react';
import { 
  fetchWorkforceSummary, 
  fetchWorkforceTrends, 
  fetchWorkforceDistribution, 
  fetchWorkforceContractExpiry, 
  fetchWorkforceIqamaExpiry, 
  fetchWorkforceExceptions 
} from '../lib/api';
import type { 
  WorkforceSummaryData, 
  WorkforceTrendsData, 
  WorkforceDistributionData, 
  ExpiryAgingData,
  DQExceptionItem 
} from '../lib/types';
import { KpiCard } from '../components/cards/KpiCard';
import { LineChartCard } from '../components/charts/LineChartCard';
import { BarChartCard } from '../components/charts/BarChartCard';
import { ExceptionTable } from '../components/tables/ExceptionTable';
import { ShieldAlert, Sparkles } from 'lucide-react';
import { formatNumber } from '../lib/formatters';

export const Workforce: React.FC = () => {
  const [summary, setSummary] = useState<WorkforceSummaryData | null>(null);
  const [trends, setTrends] = useState<WorkforceTrendsData | null>(null);
  const [distribution, setDistribution] = useState<WorkforceDistributionData | null>(null);
  const [contractExpiry, setContractExpiry] = useState<ExpiryAgingData | null>(null);
  const [iqamaExpiry, setIqamaExpiry] = useState<ExpiryAgingData | null>(null);
  const [exceptions, setExceptions] = useState<DQExceptionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [sumData, trData, distData, ceData, ieData, excData] = await Promise.all([
          fetchWorkforceSummary(),
          fetchWorkforceTrends(),
          fetchWorkforceDistribution(),
          fetchWorkforceContractExpiry(),
          fetchWorkforceIqamaExpiry(),
          fetchWorkforceExceptions()
        ]);
        setSummary(sumData);
        setTrends(trData);
        setDistribution(distData);
        setContractExpiry(ceData);
        setIqamaExpiry(ieData);
        setExceptions(excData.exceptions);
      } catch (err: any) {
        console.error(err);
        setError(err.message || 'Failed to load workforce dashboard data');
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
        <p className="text-sm font-semibold tracking-wide">Loading Workforce Dashboard...</p>
      </div>
    );
  }

  if (error || !summary || !trends || !distribution || !contractExpiry || !iqamaExpiry) {
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

  // Row 1: Primary KPIs
  const primaryKpis = summary.kpis.filter(k => 
    ['active_headcount', 'saudi_headcount', 'non_saudi_headcount', 'saudization_rate', 'probation_count'].includes(k.key)
  );

  // Row 2: Risk and DQ KPIs
  const riskKpis = summary.kpis.filter(k => 
    ['contract_expiring_30', 'iqama_expiring_30', 'missing_manager_count', 'missing_project_count', 'missing_cost_center_count'].includes(k.key)
  );

  // Prepare Expiry Aging Chart Arrays
  const expiryCategories = ['Expired', '0-30 Days', '31-60 Days', '61-90 Days', '90+ Days', 'Missing Date'];
  const contractExpiryValues = [
    contractExpiry.expired,
    contractExpiry["0_30"],
    contractExpiry["31_60"],
    contractExpiry["61_90"],
    contractExpiry["90_plus"],
    contractExpiry.missing_date
  ];

  const iqamaExpiryValues = [
    iqamaExpiry.expired,
    iqamaExpiry["0_30"],
    iqamaExpiry["31_60"],
    iqamaExpiry["61_90"],
    iqamaExpiry["90_plus"],
    iqamaExpiry.missing_date
  ];

  return (
    <div className="space-y-8 animate-fadeIn text-foreground">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            Workforce Command Center
            <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-primary/10 border border-primary/20 text-primary font-bold uppercase tracking-wider">
              <Sparkles className="w-3 h-3 animate-spin" /> Live Metrics
            </span>
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Workforce size demographics, contract audit and Saudization metrics.
          </p>
        </div>
      </div>

      {/* Row 1: Primary Workforce KPI Cards */}
      <div className="space-y-3">
        <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Primary Workforce Indicators</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {primaryKpis.map(kpi => (
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
      </div>

      {/* Row 2: Risk and Data Quality KPI Cards */}
      <div className="space-y-3">
        <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Database Completeness & Expiry Risks</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {riskKpis.map(kpi => (
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
      </div>

      {/* Row 3: Headcount Trend & Saudi/Non-Saudi Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LineChartCard
          title="Active Headcount Growth Trend"
          xAxisData={trends.months}
          seriesData={trends.headcount_trend}
          seriesName="Headcount"
          color="#38bdf8"
          valueFormatter={(val) => `${formatNumber(val)} employees`}
        />
        <BarChartCard
          title="Saudi vs Non-Saudi Demographic Distribution"
          xAxisData={distribution.nationality_group.labels}
          seriesData={distribution.nationality_group.values}
          seriesName="Employees"
          color="#10b981"
          valueFormatter={(val) => `${formatNumber(val)} employees`}
        />
      </div>

      {/* Row 4: Department & Project Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <BarChartCard
          title="Active Headcount by Department"
          xAxisData={distribution.department.labels}
          seriesData={distribution.department.values}
          seriesName="Employees"
          color="#6366f1"
          valueFormatter={(val) => `${formatNumber(val)} employees`}
        />
        <BarChartCard
          title="Active Headcount by Assigned Project"
          xAxisData={distribution.project.labels}
          seriesData={distribution.project.values}
          seriesName="Employees"
          color="#a855f7"
          valueFormatter={(val) => `${formatNumber(val)} employees`}
        />
      </div>

      {/* Row 5: Contract Expiry & Iqama Expiry Aging */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <BarChartCard
          title="Contract Expiry Aging Profile"
          xAxisData={expiryCategories}
          seriesData={contractExpiryValues}
          seriesName="Contracts"
          color="#f59e0b"
          valueFormatter={(val) => `${formatNumber(val)} contracts`}
        />
        <BarChartCard
          title="Iqama Expiry Aging Profile"
          xAxisData={expiryCategories}
          seriesData={iqamaExpiryValues}
          seriesName="Iqamas"
          color="#ef4444"
          valueFormatter={(val) => `${formatNumber(val)} iqamas`}
        />
      </div>

      {/* Row 6: Workforce Exceptions Table */}
      <div className="space-y-4">
        <div>
          <h2 className="text-sm font-bold uppercase tracking-wider text-foreground">Workforce Exceptions requiring review</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Audit logs tracking contract expiries, expired Iqamas, and missing employee master attributes.
          </p>
        </div>
        <ExceptionTable data={exceptions} />
      </div>
    </div>
  );
};

export default Workforce;
