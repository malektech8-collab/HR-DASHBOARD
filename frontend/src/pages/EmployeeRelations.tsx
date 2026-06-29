import React, { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { 
  fetchErSummary, 
  fetchErTrends, 
  fetchErByProject, 
  fetchErByDepartment, 
  fetchErCaseTypes, 
  fetchErStatus, 
  fetchErSla, 
  fetchErAging, 
  fetchErExceptions 
} from '../lib/api';
import type { 
  ErSummaryData, 
  ErTrendsData, 
  ErCasesByProjectData, 
  ErCasesByDepartmentData, 
  ErCaseTypeData, 
  ErCaseStatusData, 
  ErSlaPerformanceData, 
  ErAgingBucketData, 
  DQExceptionItem 
} from '../lib/types';
import { KpiCard } from '../components/cards/KpiCard';
import { ExceptionTable } from '../components/tables/ExceptionTable';
import { Scale, ShieldAlert, FileText, CheckCircle2, RefreshCw } from 'lucide-react';

export const EmployeeRelations: React.FC = () => {
  const [summary, setSummary] = useState<ErSummaryData | null>(null);
  const [trends, setTrends] = useState<ErTrendsData | null>(null);
  const [byProject, setByProject] = useState<ErCasesByProjectData | null>(null);
  const [byDepartment, setByDepartment] = useState<ErCasesByDepartmentData | null>(null);
  const [caseTypes, setCaseTypes] = useState<ErCaseTypeData | null>(null);
  const [caseStatus, setCaseStatus] = useState<ErCaseStatusData | null>(null);
  const [slaPerf, setSlaPerf] = useState<ErSlaPerformanceData | null>(null);
  const [agingBuckets, setAgingBuckets] = useState<ErAgingBucketData | null>(null);
  const [exceptions, setExceptions] = useState<DQExceptionItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [
        sumRes, trendRes, projRes, deptRes, typeRes, statusRes, slaRes, agingRes, excRes
      ] = await Promise.all([
        fetchErSummary(),
        fetchErTrends(),
        fetchErByProject(),
        fetchErByDepartment(),
        fetchErCaseTypes(),
        fetchErStatus(),
        fetchErSla(),
        fetchErAging(),
        fetchErExceptions()
      ]);

      setSummary(sumRes);
      setTrends(trendRes);
      setByProject(projRes);
      setByDepartment(deptRes);
      setCaseTypes(typeRes);
      setCaseStatus(statusRes);
      setSlaPerf(slaRes);
      setAgingBuckets(agingRes);
      setExceptions(excRes.exceptions);
    } catch (err: any) {
      console.error("Error loading ER page data:", err);
      setError(err?.message || "Failed to load Employee Relations dashboard data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] gap-4">
        <RefreshCw className="w-10 h-10 text-primary animate-spin" />
        <span className="text-sm text-muted-foreground font-semibold">Compiling Employee Relations metrics...</span>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="p-6 bg-critical/5 border border-critical/20 rounded-xl max-w-2xl mx-auto my-12 text-center">
        <ShieldAlert className="w-12 h-12 text-critical mx-auto mb-4" />
        <h2 className="text-lg font-bold text-foreground mb-2">Failed to Load Dashboard</h2>
        <p className="text-sm text-muted-foreground mb-6">{error || "Data is currently unavailable."}</p>
        <button 
          onClick={loadData}
          className="px-4 py-2 bg-primary text-primary-foreground font-semibold rounded-lg text-sm transition-all hover:opacity-90"
        >
          Retry
        </button>
      </div>
    );
  }

  // Map KPIs lists to easy-to-read cards
  const getKpi = (key: string) => {
    return summary.kpis.find(k => k.key === key) || {
      key,
      label: key.replace(/_/g, ' '),
      value: 0,
      unit: '',
      status: 'neutral' as const
    };
  };

  const openCasesKpi = getKpi("total_open_er_cases");
  const newCasesKpi = getKpi("new_cases_this_month");
  const closedCasesKpi = getKpi("closed_cases_this_month");
  const avgAgingKpi = getKpi("average_case_aging_days");
  const overdueCasesKpi = getKpi("overdue_cases");
  const erSlaKpi = getKpi("sla_compliance_pct");
  const disciplinaryKpi = getKpi("disciplinary_cases");
  const grievanceKpi = getKpi("grievance_cases");
  const laborKpi = getKpi("labor_cases");
  const escalatedKpi = getKpi("escalated_cases");
  const erExceptionKpi = getKpi("er_exception_count");

  // Chart 1: Monthly Cases Trend Options
  const trendMonths = trends?.trends.map(t => t.period) || [];
  const trendNewCases = trends?.trends.map(t => t.new_cases) || [];
  const trendClosedCases = trends?.trends.map(t => t.closed_cases) || [];

  const trendOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#0f172a',
      borderColor: '#334155',
      textStyle: { color: '#f8fafc' }
    },
    legend: {
      data: ['New Cases', 'Closed Cases'],
      textStyle: { color: '#94a3b8' },
      bottom: 0
    },
    grid: { left: '3%', right: '4%', bottom: '12%', top: '8%', containLabel: true },
    xAxis: {
      type: 'category',
      data: trendMonths,
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: { color: '#94a3b8' }
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: '#1e293b' } }
    },
    series: [
      {
        name: 'New Cases',
        type: 'line',
        data: trendNewCases,
        smooth: true,
        itemStyle: { color: '#3b82f6' }, // Blue
        lineStyle: { width: 3 }
      },
      {
        name: 'Closed Cases',
        type: 'line',
        data: trendClosedCases,
        smooth: true,
        itemStyle: { color: '#10b981' }, // Green
        lineStyle: { width: 3 }
      }
    ]
  };

  // Chart 2: Cases by Project (Horizontal Bar)
  const projectLabels = byProject?.projects.map(p => p.project) || [];
  const projectTotal = byProject?.projects.map(p => p.total_cases) || [];
  const projectOpen = byProject?.projects.map(p => p.open_cases) || [];

  const projectOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: '#0f172a',
      borderColor: '#334155',
      textStyle: { color: '#f8fafc' }
    },
    legend: {
      data: ['Total Cases', 'Open Cases'],
      textStyle: { color: '#94a3b8' },
      bottom: 0
    },
    grid: { left: '3%', right: '4%', bottom: '12%', top: '8%', containLabel: true },
    xAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: '#1e293b' } }
    },
    yAxis: {
      type: 'category',
      data: projectLabels,
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: { color: '#94a3b8' }
    },
    series: [
      {
        name: 'Total Cases',
        type: 'bar',
        data: projectTotal,
        itemStyle: { color: 'rgba(59, 130, 246, 0.4)', borderRadius: [0, 4, 4, 0] }
      },
      {
        name: 'Open Cases',
        type: 'bar',
        data: projectOpen,
        itemStyle: { color: '#f59e0b', borderRadius: [0, 4, 4, 0] }
      }
    ]
  };

  // Chart 3: Cases by Department (Vertical Bar)
  const deptLabels = byDepartment?.departments.map(d => d.department) || [];
  const deptTotal = byDepartment?.departments.map(d => d.total_cases) || [];
  const deptCompliance = byDepartment?.departments.map(d => d.compliance_pct) || [];

  const departmentOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#0f172a',
      borderColor: '#334155',
      textStyle: { color: '#f8fafc' }
    },
    legend: {
      data: ['Total Cases', 'SLA Compliance %'],
      textStyle: { color: '#94a3b8' },
      bottom: 0
    },
    grid: { left: '3%', right: '4%', bottom: '12%', top: '8%', containLabel: true },
    xAxis: {
      type: 'category',
      data: deptLabels,
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: { color: '#94a3b8' }
    },
    yAxis: [
      {
        type: 'value',
        name: 'Cases',
        nameTextStyle: { color: '#94a3b8' },
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { color: '#94a3b8' },
        splitLine: { lineStyle: { color: '#1e293b' } }
      },
      {
        type: 'value',
        name: 'Compliance %',
        min: 0,
        max: 100,
        nameTextStyle: { color: '#94a3b8' },
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { formatter: '{value}%', color: '#94a3b8' },
        splitLine: { show: false }
      }
    ],
    series: [
      {
        name: 'Total Cases',
        type: 'bar',
        data: deptTotal,
        itemStyle: { color: '#a855f7', borderRadius: [4, 4, 0, 0] } // Purple
      },
      {
        name: 'SLA Compliance %',
        type: 'line',
        yAxisIndex: 1,
        data: deptCompliance,
        itemStyle: { color: '#10b981' },
        lineStyle: { width: 3 },
        symbolSize: 8
      }
    ]
  };

  // Chart 4: Case Type Donut
  const caseTypeData = caseTypes?.case_types.map(t => ({
    name: t.case_type,
    value: t.case_count
  })) || [];

  const caseTypeOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: '#0f172a',
      borderColor: '#334155',
      textStyle: { color: '#f8fafc' }
    },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'center',
      textStyle: { color: '#94a3b8' }
    },
    series: [
      {
        name: 'Case Type',
        type: 'pie',
        radius: ['50%', '70%'],
        center: ['40%', '50%'],
        avoidLabelOverlap: false,
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 13, fontWeight: 'bold', formatter: '{b}\n{d}%', color: '#f8fafc' }
        },
        data: caseTypeData,
        color: ['#a855f7', '#f59e0b', '#ef4444', '#3b82f6']
      }
    ]
  };

  // Chart 5: Case Status Donut
  const caseStatusData = caseStatus?.statuses.map(s => ({
    name: s.case_status,
    value: s.case_count
  })) || [];

  const caseStatusOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: '#0f172a',
      borderColor: '#334155',
      textStyle: { color: '#f8fafc' }
    },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'center',
      textStyle: { color: '#94a3b8' }
    },
    series: [
      {
        name: 'Case Status',
        type: 'pie',
        radius: ['50%', '70%'],
        center: ['40%', '50%'],
        avoidLabelOverlap: false,
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 13, fontWeight: 'bold', formatter: '{b}\n{d}%', color: '#f8fafc' }
        },
        data: caseStatusData,
        color: ['#10b981', '#3b82f6', '#f59e0b', '#64748b']
      }
    ]
  };

  // Chart 6: SLA Performance Breakdown (Separate ER vs HR)
  const erSlaItems = slaPerf?.performance.filter(p => p.category_type === 'ER') || [];
  const hrSlaItems = slaPerf?.performance.filter(p => p.category_type === 'HR_REQ') || [];

  const slaCategories = [...erSlaItems.map(p => p.category), ...hrSlaItems.map(p => p.category)];
  const slaValues = [...erSlaItems.map(p => p.compliance_pct), ...hrSlaItems.map(p => p.compliance_pct)];
  const slaTypes = [...erSlaItems.map(() => 'ER Case'), ...hrSlaItems.map(() => 'HR Request')];

  const slaPerfOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const item = params[0];
        const idx = item.dataIndex;
        return `<div class="p-1">
          <span class="font-bold text-xs block">${item.name} (${slaTypes[idx]})</span>
          <span class="text-xs text-healthy font-semibold">SLA Achievement: ${item.value}%</span>
        </div>`;
      },
      backgroundColor: '#0f172a',
      borderColor: '#334155',
      textStyle: { color: '#f8fafc' }
    },
    grid: { left: '3%', right: '4%', bottom: '5%', top: '8%', containLabel: true },
    xAxis: {
      type: 'value',
      max: 100,
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: { formatter: '{value}%', color: '#94a3b8' },
      splitLine: { lineStyle: { color: '#1e293b' } }
    },
    yAxis: {
      type: 'category',
      data: slaCategories,
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: { color: '#94a3b8' }
    },
    series: [
      {
        name: 'SLA Compliance %',
        type: 'bar',
        data: slaValues,
        itemStyle: {
          color: (params: any) => {
            const val = params.value;
            if (val >= 90) return '#10b981'; // Green
            if (val >= 75) return '#f59e0b'; // Amber
            return '#ef4444'; // Red
          },
          borderRadius: [0, 4, 4, 0]
        }
      }
    ]
  };

  // Chart 7: Aging Buckets (Horizontal Bar)
  const bucketOrder = ['0_3_days', '4_7_days', '8_14_days', '15_30_days', '30_plus_days'];
  const bucketLabels = ['0-3 Days', '4-7 Days', '8-14 Days', '15-30 Days', '30+ Days'];
  const bucketCounts = bucketOrder.map(b => {
    const found = agingBuckets?.buckets.find(item => item.aging_bucket === b);
    return found ? found.case_count : 0;
  });

  const agingOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: '#0f172a',
      borderColor: '#334155',
      textStyle: { color: '#f8fafc' }
    },
    grid: { left: '3%', right: '4%', bottom: '5%', top: '8%', containLabel: true },
    xAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: '#1e293b' } }
    },
    yAxis: {
      type: 'category',
      data: bucketLabels,
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: { color: '#94a3b8' }
    },
    series: [
      {
        name: 'Open Cases',
        type: 'bar',
        data: bucketCounts,
        itemStyle: { color: '#f59e0b', borderRadius: [0, 4, 4, 0] }
      }
    ]
  };

  return (
    <div className="space-y-6">
      {/* Header Panel */}
      <div className="bg-card border border-border rounded-xl p-6 shadow-md flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary/10 text-primary rounded-xl">
            <Scale className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">Employee Relations & SLA Command Center</h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Legal disputes, grievance investigations, disciplinary audits, and HR Operations SLA metrics.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <span className="text-[10px] text-muted-foreground block font-semibold uppercase tracking-wider">Report Period</span>
            <span className="text-sm font-bold text-foreground bg-muted border border-border px-2.5 py-1 rounded-lg block mt-0.5">
              {summary.report_month}
            </span>
          </div>
          <button 
            onClick={loadData}
            className="p-2.5 bg-muted border border-border text-foreground hover:bg-muted/80 rounded-lg transition-colors"
            title="Reload Data"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Row 1: KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <KpiCard
          label={openCasesKpi.label}
          value={openCasesKpi.value}
          unit={openCasesKpi.unit}
          status={openCasesKpi.status}
        />
        <KpiCard
          label={newCasesKpi.label}
          value={newCasesKpi.value}
          unit={newCasesKpi.unit}
          status={newCasesKpi.status}
        />
        <KpiCard
          label={closedCasesKpi.label}
          value={closedCasesKpi.value}
          unit={closedCasesKpi.unit}
          status={closedCasesKpi.status}
        />
        <KpiCard
          label={avgAgingKpi.label}
          value={avgAgingKpi.value}
          unit={avgAgingKpi.unit}
          status={avgAgingKpi.status}
        />
        <KpiCard
          label={overdueCasesKpi.label}
          value={overdueCasesKpi.value}
          unit={overdueCasesKpi.unit}
          status={overdueCasesKpi.status}
        />
      </div>

      {/* Row 2: Secondary KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
        <KpiCard
          label={erSlaKpi.label}
          value={erSlaKpi.value}
          unit={erSlaKpi.unit}
          status={erSlaKpi.status}
        />
        <KpiCard
          label={disciplinaryKpi.label}
          value={disciplinaryKpi.value}
          unit={disciplinaryKpi.unit}
          status={disciplinaryKpi.status}
        />
        <KpiCard
          label={grievanceKpi.label}
          value={grievanceKpi.value}
          unit={grievanceKpi.unit}
          status={grievanceKpi.status}
        />
        <KpiCard
          label={laborKpi.label}
          value={laborKpi.value}
          unit={laborKpi.unit}
          status={laborKpi.status}
        />
        <KpiCard
          label={escalatedKpi.label}
          value={escalatedKpi.value}
          unit={escalatedKpi.unit}
          status={escalatedKpi.status}
        />
        <KpiCard
          label={erExceptionKpi.label}
          value={erExceptionKpi.value}
          unit={erExceptionKpi.unit}
          status={erExceptionKpi.status}
        />
      </div>

      {/* Row 3: Trends (New vs Closed Line Chart) */}
      <div className="bg-card border border-border rounded-xl p-5">
        <h3 className="font-bold text-sm text-foreground flex items-center gap-2">
          <FileText className="w-5 h-5 text-primary" />
          ER Case Flow Trends
        </h3>
        <p className="text-xs text-muted-foreground mt-0.5">Timeline monitoring of new cases opened vs resolved case closures.</p>
        <div className="h-[300px] w-full mt-4">
          <ReactECharts option={trendOption} style={{ height: '100%', width: '100%' }} />
        </div>
      </div>

      {/* Row 4: Project and Department breakdowns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card border border-border rounded-xl p-5">
          <h3 className="font-bold text-sm text-foreground">Cases by Subject Project</h3>
          <p className="text-xs text-muted-foreground mt-0.5">Total and open case distributions across workforce projects.</p>
          <div className="h-[300px] w-full mt-4">
            <ReactECharts option={projectOption} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>
        <div className="bg-card border border-border rounded-xl p-5">
          <h3 className="font-bold text-sm text-foreground">Cases by Subject Department</h3>
          <p className="text-xs text-muted-foreground mt-0.5">Total caseload and SLA compliance percentage by department.</p>
          <div className="h-[300px] w-full mt-4">
            <ReactECharts option={departmentOption} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>
      </div>

      {/* Row 5: Case type and Case status distributions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card border border-border rounded-xl p-5">
          <h3 className="font-bold text-sm text-foreground">Case Type Segmentation</h3>
          <p className="text-xs text-muted-foreground mt-0.5">Disciplinary, Grievance, and Labor Cases distribution.</p>
          <div className="h-[250px] w-full mt-4">
            <ReactECharts option={caseTypeOption} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>
        <div className="bg-card border border-border rounded-xl p-5">
          <h3 className="font-bold text-sm text-foreground">Case Status Distribution</h3>
          <p className="text-xs text-muted-foreground mt-0.5">Current state of active, pending, or closed ER investigations.</p>
          <div className="h-[250px] w-full mt-4">
            <ReactECharts option={caseStatusOption} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>
      </div>

      {/* Row 6: SLA Performance and Aging Buckets */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card border border-border rounded-xl p-5">
          <h3 className="font-bold text-sm text-foreground">SLA Performance Breakdown</h3>
          <p className="text-xs text-muted-foreground mt-0.5">SLA achievement percentage separately for ER Case Types and HR Request Types.</p>
          <div className="h-[250px] w-full mt-4">
            <ReactECharts option={slaPerfOption} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>
        <div className="bg-card border border-border rounded-xl p-5">
          <h3 className="font-bold text-sm text-foreground">Open Case Aging Buckets</h3>
          <p className="text-xs text-muted-foreground mt-0.5">Classification of unresolved cases by days elapsed since creation.</p>
          <div className="h-[250px] w-full mt-4">
            <ReactECharts option={agingOption} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>
      </div>

      {/* Row 7: Exceptions Log Table */}
      <div className="bg-card border border-border rounded-xl p-5">
        <h3 className="font-bold text-sm text-foreground flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-critical" />
          Employee Relations Exceptions Audit Log
        </h3>
        <p className="text-xs text-muted-foreground mt-0.5 mb-4">
          Unreconciled legal cases, missing target dates, overdue open cases, and inactive owners or subjects.
        </p>
        <ExceptionTable data={exceptions} />
      </div>
    </div>
  );
};
