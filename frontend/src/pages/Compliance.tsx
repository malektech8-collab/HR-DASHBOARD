import React, { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { 
  fetchComplianceSummary, 
  fetchSaudizationSummary, 
  fetchSaudizationByProject, 
  fetchSaudizationByDepartment, 
  fetchDocumentExpiry, 
  fetchGosiStatus, 
  fetchWpsStatus, 
  fetchComplianceExceptions 
} from '../lib/api';
import type { 
  ComplianceSummaryData, 
  SaudizationSummaryData, 
  SaudizationByProjectData, 
  SaudizationByDepartmentData, 
  DocumentExpiryData, 
  GosiStatusData, 
  WpsStatusData, 
  DQExceptionItem 
} from '../lib/types';
import { KpiCard } from '../components/cards/KpiCard';
import { ExceptionTable } from '../components/tables/ExceptionTable';
import { ShieldCheck, ShieldAlert, FileText, CheckCircle2 } from 'lucide-react';


export const Compliance: React.FC = () => {
  const [summary, setSummary] = useState<ComplianceSummaryData | null>(null);
  const [trends, setTrends] = useState<SaudizationSummaryData | null>(null);
  const [projects, setProjects] = useState<SaudizationByProjectData | null>(null);
  const [departments, setDepartments] = useState<SaudizationByDepartmentData | null>(null);
  const [expiry, setExpiry] = useState<DocumentExpiryData | null>(null);
  const [gosi, setGosi] = useState<GosiStatusData | null>(null);
  const [wps, setWps] = useState<WpsStatusData | null>(null);
  const [exceptions, setExceptions] = useState<DQExceptionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [sumData, trData, projData, deptData, expData, gosiData, wpsData, excData] = await Promise.all([
          fetchComplianceSummary(),
          fetchSaudizationSummary(),
          fetchSaudizationByProject(),
          fetchSaudizationByDepartment(),
          fetchDocumentExpiry(),
          fetchGosiStatus(),
          fetchWpsStatus(),
          fetchComplianceExceptions()
        ]);
        setSummary(sumData);
        setTrends(trData);
        setProjects(projData);
        setDepartments(deptData);
        setExpiry(expData);
        setGosi(gosiData);
        setWps(wpsData);
        setExceptions(excData.exceptions);
      } catch (err: any) {
        console.error(err);
        setError(err.message || 'Failed to load compliance dashboard data');
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
        <p className="text-sm font-semibold tracking-wide">Loading Compliance Dashboard...</p>
      </div>
    );
  }

  if (error || !summary || !trends || !projects || !departments || !expiry || !gosi || !wps) {
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

  const getKpi = (key: string) => {
    return summary.kpis.find(k => k.key === key) || {
      key,
      label: key,
      value: 0,
      unit: '',
      status: 'neutral' as const
    };
  };

  const saudizationPctKpi = getKpi('saudization_pct');
  const saudiHckpi = getKpi('saudi_headcount');
  const nonSaudiHckpi = getKpi('non_saudi_headcount');
  const missingNatKpi = getKpi('employees_missing_nationality');
  const iqama30Kpi = getKpi('iqamas_expiring_30');
  const wp30Kpi = getKpi('work_permits_expiring_30');
  const iqamaExpiredKpi = getKpi('iqamas_expired');
  const wpExpiredKpi = getKpi('work_permits_expired');
  const gosiMissingKpi = getKpi('gosi_missing_count');
  const wpsExceptionsKpi = getKpi('wps_exception_count');
  const complianceExceptionsKpi = getKpi('compliance_exception_count');

  // Chart 1: Saudization Trend
  const trendOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#090d16',
      borderColor: '#1e293b',
      borderWidth: 1,
      textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'Inter, sans-serif' }
    },
    legend: {
      data: ['Saudi Headcount', 'Non-Saudi Headcount', 'Saudization %'],
      textStyle: { color: '#94a3b8', fontSize: 11, fontFamily: 'Inter, sans-serif' },
      bottom: '0%'
    },
    grid: { top: '15%', left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: trends.trends.map(t => t.period),
      axisLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', fontSize: 11, fontFamily: 'Inter, sans-serif' }
    },
    yAxis: [
      {
        type: 'value',
        name: 'Headcount',
        nameTextStyle: { color: '#64748b', fontSize: 10 },
        splitLine: { lineStyle: { color: '#1e293b' } },
        axisLabel: { color: '#64748b', fontSize: 11 }
      },
      {
        type: 'value',
        name: 'Saudization %',
        nameTextStyle: { color: '#64748b', fontSize: 10 },
        splitLine: { show: false },
        axisLabel: { 
          color: '#64748b', 
          fontSize: 11,
          formatter: '{value}%'
        }
      }
    ],
    series: [
      {
        name: 'Saudi Headcount',
        type: 'bar',
        stack: 'headcount',
        data: trends.trends.map(t => t.saudi_headcount),
        itemStyle: { color: '#10b981' }
      },
      {
        name: 'Non-Saudi Headcount',
        type: 'bar',
        stack: 'headcount',
        data: trends.trends.map(t => t.non_saudi_headcount),
        itemStyle: { color: '#3b82f6' }
      },
      {
        name: 'Saudization %',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbolSize: 8,
        data: trends.trends.map(t => t.saudization_pct),
        itemStyle: { color: '#f59e0b' },
        lineStyle: { width: 3 }
      }
    ]
  };

  // Chart 2: Saudi vs Non-Saudi pie
  const distributionOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: '#090d16',
      borderColor: '#1e293b',
      borderWidth: 1,
      textStyle: { color: '#f8fafc', fontSize: 12 }
    },
    legend: {
      orient: 'horizontal',
      bottom: '0%',
      textStyle: { color: '#94a3b8', fontSize: 11 }
    },
    series: [
      {
        name: 'Nationality Distribution',
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: '#0f172a',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 16,
            fontWeight: 'bold',
            color: '#f8fafc'
          }
        },
        labelLine: {
          show: false
        },
        data: [
          { value: saudiHckpi.value, name: 'Saudi', itemStyle: { color: '#10b981' } },
          { value: nonSaudiHckpi.value, name: 'Non-Saudi', itemStyle: { color: '#3b82f6' } },
          { value: missingNatKpi.value, name: 'Missing Nationality', itemStyle: { color: '#ef4444' } }
        ]
      }
    ]
  };

  // Chart 3: Saudization by Project
  const projectOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: '#090d16',
      borderColor: '#1e293b',
      borderWidth: 1,
      textStyle: { color: '#f8fafc', fontSize: 12 }
    },
    grid: { top: '10%', left: '3%', right: '8%', bottom: '5%', containLabel: true },
    xAxis: {
      type: 'value',
      max: 100,
      splitLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', formatter: '{value}%' }
    },
    yAxis: {
      type: 'category',
      data: projects.projects.map(p => p.project),
      axisLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', fontSize: 11 }
    },
    series: [
      {
        name: 'Saudization %',
        type: 'bar',
        data: projects.projects.map(p => p.saudization_pct),
        itemStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 1, y2: 0,
            colorStops: [
              { offset: 0, color: '#047857' },
              { offset: 1, color: '#10b981' }
            ]
          },
          borderRadius: [0, 4, 4, 0]
        },
        label: {
          show: true,
          position: 'right',
          color: '#f8fafc',
          formatter: '{c}%',
          fontSize: 10
        }
      }
    ]
  };

  // Chart 4: Saudization by Department
  const departmentOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: '#090d16',
      borderColor: '#1e293b',
      borderWidth: 1,
      textStyle: { color: '#f8fafc', fontSize: 12 }
    },
    grid: { top: '10%', left: '3%', right: '8%', bottom: '5%', containLabel: true },
    xAxis: {
      type: 'value',
      max: 100,
      splitLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', formatter: '{value}%' }
    },
    yAxis: {
      type: 'category',
      data: departments.departments.map(d => d.department),
      axisLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', fontSize: 11 }
    },
    series: [
      {
        name: 'Saudization %',
        type: 'bar',
        data: departments.departments.map(d => d.saudization_pct),
        itemStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 1, y2: 0,
            colorStops: [
              { offset: 0, color: '#1d4ed8' },
              { offset: 1, color: '#3b82f6' }
            ]
          },
          borderRadius: [0, 4, 4, 0]
        },
        label: {
          show: true,
          position: 'right',
          color: '#f8fafc',
          formatter: '{c}%',
          fontSize: 10
        }
      }
    ]
  };

  // Chart 5: Expiry Buckets
  const expiryBuckets = ['expired', '0_30', '31_60', '61_90', '90_plus', 'missing_date'];
  const getExpiryLabel = (b: string) => {
    switch (b) {
      case 'expired': return 'Expired';
      case '0_30': return '0-30 Days';
      case '31_60': return '31-60 Days';
      case '61_90': return '61-90 Days';
      case '90_plus': return '90+ Days';
      case 'missing_date': return 'Missing Date';
      default: return b;
    }
  };

  const documentExpiryOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#090d16',
      borderColor: '#1e293b',
      borderWidth: 1,
      textStyle: { color: '#f8fafc', fontSize: 12 }
    },
    legend: {
      data: ['Iqama Expiry', 'Work Permit Expiry'],
      textStyle: { color: '#94a3b8', fontSize: 11 },
      bottom: '0%'
    },
    grid: { top: '15%', left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: expiryBuckets.map(getExpiryLabel),
      axisLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b' }
    },
    series: [
      {
        name: 'Iqama Expiry',
        type: 'bar',
        data: expiryBuckets.map(eb => {
          const item = expiry.buckets.find(b => b.expiry_bucket === eb);
          return item ? item.iqama_count : 0;
        }),
        itemStyle: { color: '#f59e0b', borderRadius: [4, 4, 0, 0] }
      },
      {
        name: 'Work Permit Expiry',
        type: 'bar',
        data: expiryBuckets.map(eb => {
          const item = expiry.buckets.find(b => b.expiry_bucket === eb);
          return item ? item.work_permit_count : 0;
        }),
        itemStyle: { color: '#ec4899', borderRadius: [4, 4, 0, 0] }
      }
    ]
  };

  // Chart 6 & 7: GOSI & WPS status distribution donuts
  const gosiOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: '#090d16',
      borderColor: '#1e293b',
      borderWidth: 1,
      textStyle: { color: '#f8fafc', fontSize: 12 }
    },
    series: [
      {
        name: 'GOSI Status',
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#0f172a',
          borderWidth: 2
        },
        label: {
          show: true,
          position: 'outside',
          color: '#64748b',
          fontSize: 10,
          formatter: '{b}\n({c})'
        },
        data: gosi.statuses.map(s => {
          let color = '#3b82f6';
          if (s.gosi_status === 'Registered') color = '#10b981';
          if (s.gosi_status === 'Not Registered') color = '#f59e0b';
          if (s.gosi_status.includes('Missing')) color = '#ef4444';
          return {
            value: s.employee_count,
            name: s.gosi_status,
            itemStyle: { color }
          };
        })
      }
    ]
  };

  const wpsOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: '#090d16',
      borderColor: '#1e293b',
      borderWidth: 1,
      textStyle: { color: '#f8fafc', fontSize: 12 }
    },
    series: [
      {
        name: 'WPS Status',
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#0f172a',
          borderWidth: 2
        },
        label: {
          show: true,
          position: 'outside',
          color: '#64748b',
          fontSize: 10,
          formatter: '{b}\n({c})'
        },
        data: wps.statuses.map(s => {
          let color = '#3b82f6';
          if (s.wps_status === 'Compliant') color = '#10b981';
          if (s.wps_status === 'Non-Compliant') color = '#ef4444';
          if (s.wps_status.includes('Missing')) color = '#f59e0b';
          return {
            value: s.headcount,
            name: s.wps_status,
            itemStyle: { color }
          };
        })
      }
    ]
  };

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <ShieldCheck className="w-7 h-7 text-primary" />
            Saudization & Compliance Command Center
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Official Saudization, GOSI, WPS compliance status, and document validity audit.
          </p>
        </div>
        <div className="px-3 py-1.5 rounded-lg border border-border bg-slate-950/20 text-xs font-semibold text-muted-foreground flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
          Report Period: {summary.report_month}
        </div>
      </div>

      {/* Row 1: KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 gap-4">
        {/* Card 1: Saudization % */}
        <div className="xl:col-span-2">
          <KpiCard
            label={saudizationPctKpi.label}
            value={saudizationPctKpi.value}
            unit={saudizationPctKpi.unit}
            status={saudizationPctKpi.status}
          />
        </div>
        <KpiCard
          label={saudiHckpi.label}
          value={saudiHckpi.value}
          unit={saudiHckpi.unit}
          status={saudiHckpi.status}
        />
        <KpiCard
          label={nonSaudiHckpi.label}
          value={nonSaudiHckpi.value}
          unit={nonSaudiHckpi.unit}
          status={nonSaudiHckpi.status}
        />
        <KpiCard
          label={missingNatKpi.label}
          value={missingNatKpi.value}
          unit={missingNatKpi.unit}
          status={missingNatKpi.status}
        />
        <KpiCard
          label={complianceExceptionsKpi.label}
          value={complianceExceptionsKpi.value}
          unit={complianceExceptionsKpi.unit}
          status={complianceExceptionsKpi.status}
        />
      </div>

      {/* Row 2: Secondary KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <KpiCard
          label={iqamaExpiredKpi.label}
          value={iqamaExpiredKpi.value}
          unit={iqamaExpiredKpi.unit}
          status={iqamaExpiredKpi.status}
        />
        <KpiCard
          label={wpExpiredKpi.label}
          value={wpExpiredKpi.value}
          unit={wpExpiredKpi.unit}
          status={wpExpiredKpi.status}
        />
        <KpiCard
          label={iqama30Kpi.label}
          value={iqama30Kpi.value}
          unit={iqama30Kpi.unit}
          status={iqama30Kpi.status}
        />
        <KpiCard
          label={wp30Kpi.label}
          value={wp30Kpi.value}
          unit={wp30Kpi.unit}
          status={wp30Kpi.status}
        />
        <KpiCard
          label={gosiMissingKpi.label}
          value={gosiMissingKpi.value}
          unit={gosiMissingKpi.unit}
          status={gosiMissingKpi.status}
        />
        <KpiCard
          label={wpsExceptionsKpi.label}
          value={wpsExceptionsKpi.value}
          unit={wpsExceptionsKpi.unit}
          status={wpsExceptionsKpi.status}
        />
      </div>

      {/* Row 3: Trends and Pie Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-card border border-border rounded-xl p-5 flex flex-col justify-between">
          <div>
            <h3 className="font-bold text-sm text-foreground flex items-center gap-1.5">
              <FileText className="w-4 h-4 text-primary" />
              Saudization Trend by Month
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Saudi and Non-Saudi active headcounts compared to cumulative Saudization percentage (Sample Mode).
            </p>
          </div>
          <div className="h-[250px] w-full mt-4">
            <ReactECharts option={trendOption} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-5 flex flex-col justify-between">
          <div>
            <h3 className="font-bold text-sm text-foreground flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-primary" />
              Saudi vs Non-Saudi Distribution
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Workforce distribution including missing nationality records.
            </p>
          </div>
          <div className="h-[250px] w-full mt-4">
            <ReactECharts option={distributionOption} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>
      </div>

      {/* Row 4: Breakdown by Project and Department */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card border border-border rounded-xl p-5">
          <h3 className="font-bold text-sm text-foreground">Saudization % by Project</h3>
          <p className="text-xs text-muted-foreground mt-0.5">Project level local talent ratios.</p>
          <div className="h-[240px] w-full mt-4">
            <ReactECharts option={projectOption} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-5">
          <h3 className="font-bold text-sm text-foreground">Saudization % by Department</h3>
          <p className="text-xs text-muted-foreground mt-0.5">Department level local talent ratios.</p>
          <div className="h-[240px] w-full mt-4">
            <ReactECharts option={departmentOption} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>
      </div>

      {/* Row 5: Document expiry aging and platform distributions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 bg-card border border-border rounded-xl p-5">
          <h3 className="font-bold text-sm text-foreground">GOSI Status Distribution</h3>
          <p className="text-xs text-muted-foreground mt-0.5">Social insurance registration audit.</p>
          <div className="h-[220px] w-full mt-4">
            <ReactECharts option={gosiOption} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>

        <div className="lg:col-span-1 bg-card border border-border rounded-xl p-5">
          <h3 className="font-bold text-sm text-foreground">WPS (Mudad) Status Distribution</h3>
          <p className="text-xs text-muted-foreground mt-0.5">Wage Protection System compliance audit.</p>
          <div className="h-[220px] w-full mt-4">
            <ReactECharts option={wpsOption} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>

        <div className="lg:col-span-1 bg-card border border-border rounded-xl p-5">
          <h3 className="font-bold text-sm text-foreground">Document Expiry Aging</h3>
          <p className="text-xs text-muted-foreground mt-0.5">Iqama and Work Permit validity buckets.</p>
          <div className="h-[220px] w-full mt-4">
            <ReactECharts option={documentExpiryOption} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>
      </div>

      {/* Row 6: Exceptions Table */}
      <div className="bg-card border border-border rounded-xl p-5">
        <h3 className="font-bold text-sm text-foreground flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-critical" />
          Compliance Exceptions Audit Log
        </h3>
        <p className="text-xs text-muted-foreground mt-0.5 mb-4">
          Unreconciled platform registrations, expired documents, and missing nationality records.
        </p>
        <ExceptionTable data={exceptions} />
      </div>
    </div>
  );
};
