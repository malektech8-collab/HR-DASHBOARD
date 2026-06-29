import React, { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { 
  fetchPayrollSummary, 
  fetchPayrollTrends, 
  fetchPayrollByProject, 
  fetchPayrollByDepartment, 
  fetchPayrollComponents, 
  fetchPayrollVariance, 
  fetchPayrollExceptions 
} from '../lib/api';
import type { 
  PayrollSummaryData, 
  PayrollTrendsData, 
  PayrollByProjectData, 
  PayrollByDepartmentData, 
  PayrollComponentsData, 
  PayrollVarianceData, 
  DQExceptionItem 
} from '../lib/types';
import { KpiCard } from '../components/cards/KpiCard';
import { ExceptionTable } from '../components/tables/ExceptionTable';
import { Sparkles, ShieldAlert, TrendingUp, TrendingDown } from 'lucide-react';
import { formatCurrency, formatPercent, formatNumber } from '../lib/formatters';

export const Payroll: React.FC = () => {
  const [summary, setSummary] = useState<PayrollSummaryData | null>(null);
  const [trends, setTrends] = useState<PayrollTrendsData | null>(null);
  const [projects, setProjects] = useState<PayrollByProjectData | null>(null);
  const [departments, setDepartments] = useState<PayrollByDepartmentData | null>(null);
  const [components, setComponents] = useState<PayrollComponentsData | null>(null);
  const [variance, setVariance] = useState<PayrollVarianceData | null>(null);
  const [exceptions, setExceptions] = useState<DQExceptionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [sumData, trData, projData, deptData, compData, varData, excData] = await Promise.all([
          fetchPayrollSummary(),
          fetchPayrollTrends(),
          fetchPayrollByProject(),
          fetchPayrollByDepartment(),
          fetchPayrollComponents(),
          fetchPayrollVariance(),
          fetchPayrollExceptions()
        ]);
        setSummary(sumData);
        setTrends(trData);
        setProjects(projData);
        setDepartments(deptData);
        setComponents(compData);
        setVariance(varData);
        setExceptions(excData.exceptions);
      } catch (err: any) {
        console.error(err);
        setError(err.message || 'Failed to load payroll dashboard data');
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
        <p className="text-sm font-semibold tracking-wide">Loading Payroll Dashboard...</p>
      </div>
    );
  }

  if (error || !summary || !trends || !projects || !departments || !components || !variance) {
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

  // Helper to find KPI by key safely
  const getKpi = (key: string) => {
    return summary.kpis.find(k => k.key === key) || {
      key,
      label: key.replace(/_/g, ' '),
      value: 0,
      unit: 'SAR',
      status: 'neutral' as const
    };
  };

  // Row 1 KPIs
  const row1Kpis = [
    getKpi('total_payroll_cost'),
    getKpi('net_payroll'),
    getKpi('employees_paid'),
    getKpi('avg_cost_per_employee'),
    getKpi('payroll_variance_pct')
  ];

  // Row 2 KPIs
  const row2Kpis = [
    getKpi('basic_salary_cost'),
    getKpi('allowances_cost'),
    getKpi('overtime_cost'),
    getKpi('deductions'),
    getKpi('payroll_exception_count')
  ];

  // Row 3: Trend Option
  const trendOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#090d16',
      borderColor: '#1e293b',
      borderWidth: 1,
      textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'Inter, sans-serif' },
      formatter: (params: any) => {
        let result = `<div style="padding: 4px 8px;">
          <div style="color: #64748b; font-size: 10px; font-weight: 600; text-transform: uppercase; margin-bottom: 6px;">${params[0].name}</div>`;
        params.forEach((item: any) => {
          result += `<div style="display: flex; justify-content: space-between; gap: 16px; margin-bottom: 4px; align-items: center;">
            <div style="display: flex; align-items: center; gap: 6px;">
              <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: ${item.color};"></span>
              <span style="color: #94a3b8; font-size: 11px;">${item.seriesName}</span>
            </div>
            <span style="font-weight: 700; font-size: 12px; color: #f8fafc;">${formatCurrency(item.value)}</span>
          </div>`;
        });
        result += `</div>`;
        return result;
      }
    },
    legend: {
      data: ['Total Payroll Cost', 'Net Payroll'],
      textStyle: { color: '#94a3b8', fontFamily: 'Inter, sans-serif', fontSize: 11 },
      bottom: '0%'
    },
    grid: { top: '8%', left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: trends.trends.map(t => t.month),
      axisLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', fontSize: 11, fontFamily: 'Inter, sans-serif' }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', fontSize: 11, fontFamily: 'Inter, sans-serif' }
    },
    series: [
      {
        name: 'Total Payroll Cost',
        data: trends.trends.map(t => t.total_payroll_cost),
        type: 'line',
        smooth: 0.3,
        itemStyle: { color: '#38bdf8' },
        lineStyle: { width: 3 },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [{ offset: 0, color: '#38bdf818' }, { offset: 1, color: '#38bdf800' }]
          }
        }
      },
      {
        name: 'Net Payroll',
        data: trends.trends.map(t => t.net_payroll),
        type: 'line',
        smooth: 0.3,
        itemStyle: { color: '#10b981' },
        lineStyle: { width: 3 },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [{ offset: 0, color: '#10b98118' }, { offset: 1, color: '#10b98100' }]
          }
        }
      }
    ]
  };

  // Row 3: Component Breakdown Option
  const componentsOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: '#090d16',
      borderColor: '#1e293b',
      borderWidth: 1,
      textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'Inter, sans-serif' },
      formatter: (params: any) => {
        return `
          <div style="padding: 4px 8px;">
            <div style="color: #64748b; font-size: 10px; font-weight: 600; text-transform: uppercase; margin-bottom: 4px;">${params.name}</div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: ${params.color};"></span>
              <span style="font-weight: 700;">${formatCurrency(params.value)}</span>
              <span style="color: #94a3b8; font-size: 11px;">(${params.percent}%)</span>
            </div>
          </div>
        `;
      }
    },
    legend: {
      orient: 'vertical',
      right: '2%',
      top: 'center',
      textStyle: { color: '#94a3b8', fontFamily: 'Inter, sans-serif', fontSize: 11 },
      icon: 'circle',
      itemGap: 10
    },
    series: [
      {
        name: 'Payroll Components',
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#0f172a',
          borderWidth: 2
        },
        label: { show: false },
        emphasis: {
          label: {
            show: false
          }
        },
        labelLine: { show: false },
        data: components.components
          .filter(c => c.component !== 'Deductions' && c.component !== 'Unreconciled / Exception Amount') // Exclude deductions and negative unreconciled amount from pie sectors
          .map(c => ({
            name: c.component,
            value: c.amount
          })),
        color: ['#6366f1', '#38bdf8', '#0ea5e9', '#06b6d4', '#f59e0b']
      }
    ]
  };

  // Row 4: Project Option
  const projectOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#090d16',
      borderColor: '#1e293b',
      borderWidth: 1,
      textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'Inter, sans-serif' },
      formatter: (params: any) => {
        const item = params[0];
        const projData = projects.projects[item.dataIndex];
        return `
          <div style="padding: 4px 8px;">
            <div style="color: #64748b; font-size: 10px; font-weight: 600; text-transform: uppercase; margin-bottom: 4px;">${item.name}</div>
            <div style="font-weight: 700; margin-bottom: 2px;">Cost: ${formatCurrency(item.value)}</div>
            <div style="color: #94a3b8; font-size: 11px;">Headcount: ${projData.headcount} employees</div>
          </div>
        `;
      }
    },
    grid: { top: '8%', left: '3%', right: '4%', bottom: '5%', containLabel: true },
    xAxis: {
      type: 'category',
      data: projects.projects.map(p => p.project),
      axisLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', fontSize: 11, fontFamily: 'Inter, sans-serif' }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', fontSize: 11, fontFamily: 'Inter, sans-serif' }
    },
    series: [
      {
        name: 'Project Payroll Cost',
        data: projects.projects.map(p => p.total_payroll_cost),
        type: 'bar',
        barWidth: '35%',
        itemStyle: {
          color: '#a855f7',
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  };

  // Row 4: Department Option
  const departmentOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#090d16',
      borderColor: '#1e293b',
      borderWidth: 1,
      textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'Inter, sans-serif' },
      formatter: (params: any) => {
        const item = params[0];
        const deptData = departments.departments[item.dataIndex];
        return `
          <div style="padding: 4px 8px;">
            <div style="color: #64748b; font-size: 10px; font-weight: 600; text-transform: uppercase; margin-bottom: 4px;">${item.name}</div>
            <div style="font-weight: 700; margin-bottom: 2px;">Cost: ${formatCurrency(item.value)}</div>
            <div style="color: #94a3b8; font-size: 11px;">Headcount: ${deptData.headcount} employees</div>
          </div>
        `;
      }
    },
    grid: { top: '8%', left: '3%', right: '4%', bottom: '5%', containLabel: true },
    xAxis: {
      type: 'category',
      data: departments.departments.map(d => d.department),
      axisLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', fontSize: 11, fontFamily: 'Inter, sans-serif' }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', fontSize: 11, fontFamily: 'Inter, sans-serif' }
    },
    series: [
      {
        name: 'Department Payroll Cost',
        data: departments.departments.map(d => d.total_payroll_cost),
        type: 'bar',
        barWidth: '35%',
        itemStyle: {
          color: '#6366f1',
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  };

  // Row 5: Overtime Project Option
  const overtimeProjectOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#090d16',
      borderColor: '#1e293b',
      borderWidth: 1,
      textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'Inter, sans-serif' },
      formatter: (params: any) => {
        const item = params[0];
        return `
          <div style="padding: 4px 8px;">
            <div style="color: #64748b; font-size: 10px; font-weight: 600; text-transform: uppercase; margin-bottom: 4px;">${item.name}</div>
            <div style="font-weight: 700;">Overtime: ${formatCurrency(item.value)}</div>
          </div>
        `;
      }
    },
    grid: { top: '8%', left: '3%', right: '4%', bottom: '5%', containLabel: true },
    xAxis: {
      type: 'category',
      data: projects.projects.map(p => p.project),
      axisLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', fontSize: 11, fontFamily: 'Inter, sans-serif' }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', fontSize: 11, fontFamily: 'Inter, sans-serif' }
    },
    series: [
      {
        name: 'Overtime Cost',
        data: projects.projects.map(p => p.overtime_cost),
        type: 'bar',
        barWidth: '35%',
        itemStyle: {
          color: '#f59e0b',
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  };

  // Filter out negative values from employee variance for highlighting anomalies
  const topVariances = variance.employees.slice(0, 5);

  return (
    <div className="space-y-8 animate-fadeIn text-foreground">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            Payroll & Cost Command Center
            <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-primary/10 border border-primary/20 text-primary font-bold uppercase tracking-wider">
              <Sparkles className="w-3 h-3 animate-pulse" /> Financials
            </span>
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Official payroll cost breakdown, salary allowances, overtime costs, deductions, and monthly variances.
          </p>
        </div>
      </div>

      {/* Row 1: Executive KPI Cards */}
      <div className="space-y-3">
        <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Executive Financial Totals</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {row1Kpis.map(kpi => (
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

      {/* Row 2: Secondary component KPIs */}
      <div className="space-y-3">
        <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Component Totals & Exceptions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {row2Kpis.map(kpi => (
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

      {/* Row 3: Trend & Component breakdown charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-card border border-border rounded-xl p-5 shadow-lg flex flex-col h-[320px]">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">Gross vs Net Payroll Trend</h3>
          <div className="flex-1 min-h-0">
            <ReactECharts option={trendOption} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>
        <div className="bg-card border border-border rounded-xl p-5 shadow-lg flex flex-col h-[320px]">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">Gross Payroll Composition</h3>
          <div className="flex-1 min-h-0 relative">
            <ReactECharts option={componentsOption} style={{ height: '100%', width: '100%' }} />
          </div>
          {summary.reconciliation.unreconciled_component_difference !== 0 && (
            <div className="mt-2 pt-2 border-t border-border/40 flex justify-between items-center text-xs">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-critical animate-pulse"></span>
                Unreconciled Exception:
              </span>
              <span className="font-bold text-critical bg-critical/5 px-2 py-0.5 rounded border border-critical/10">
                {formatCurrency(summary.reconciliation.unreconciled_component_difference)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Row 4: Project & Department cost distributions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card border border-border rounded-xl p-5 shadow-lg flex flex-col h-[300px]">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">Payroll Cost by Assigned Project</h3>
          <div className="flex-1 min-h-0">
            <ReactECharts option={projectOption} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>
        <div className="bg-card border border-border rounded-xl p-5 shadow-lg flex flex-col h-[300px]">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">Payroll Cost by Department</h3>
          <div className="flex-1 min-h-0">
            <ReactECharts option={departmentOption} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>
      </div>

      {/* Row 5: Overtime & Variance analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Overtime by Project */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-lg flex flex-col h-[320px]">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">Overtime Cost by Project</h3>
          <div className="flex-1 min-h-0">
            <ReactECharts option={overtimeProjectOption} style={{ height: '100%', width: '100%' }} />
          </div>
        </div>

        {/* Variance Analysis */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-lg flex flex-col h-[320px] overflow-hidden">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Top MoM Employee Variances</h3>
          <div className="flex-1 overflow-y-auto pr-1 space-y-3">
            {topVariances.map(emp => {
              const isIncrease = emp.change_amount > 0;
              const isLargeChange = Math.abs(emp.change_amount) > 2000;
              return (
                <div key={emp.employee_id} className="flex items-center justify-between p-3 rounded-lg border border-border/60 bg-slate-950/10 hover:bg-slate-950/20 transition-all">
                  <div className="space-y-1">
                    <div className="text-sm font-semibold flex items-center gap-1.5">
                      {emp.employee_name || 'Unknown Employee'}
                      <span className="text-[10px] text-muted-foreground font-mono bg-muted px-1 py-0.5 rounded">{emp.employee_id}</span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Prev: <span className="text-foreground">{formatCurrency(emp.prev_amount)}</span> | Curr: <span className="text-foreground font-semibold">{formatCurrency(emp.curr_amount)}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`text-sm font-bold flex items-center justify-end gap-1 ${
                      isLargeChange 
                        ? 'text-warning' 
                        : isIncrease 
                          ? 'text-healthy' 
                          : 'text-muted-foreground'
                    }`}>
                      {isIncrease ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                      {isIncrease ? '+' : ''}{formatCurrency(emp.change_amount)}
                    </div>
                    <div className="text-[10px] text-muted-foreground">
                      {formatPercent(emp.change_pct * 100)} MoM change
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Row 6: Reconciliation & Exceptions Table */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Reconciliation Report Card */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-lg flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-foreground">Payroll Reconciliation Report</h3>
            <p className="text-[11px] text-muted-foreground mt-0.5">Audit log matching ledger costs, components, projects and departments.</p>
          </div>
          <div className="mt-4 flex-1 divide-y divide-border/40 text-xs">
            <div className="py-2 flex justify-between">
              <span className="text-muted-foreground">Total Gross Payroll (Ledger)</span>
              <span className="font-bold text-foreground">{formatCurrency(summary.reconciliation.total_gross_payroll)}</span>
            </div>
            <div className="py-2 flex justify-between">
              <span className="text-muted-foreground">Sum of Gross Components</span>
              <span className="font-semibold text-foreground">{formatCurrency(summary.reconciliation.sum_displayed_components)}</span>
            </div>
            <div className="py-2 flex justify-between items-center">
              <span className="text-muted-foreground">Unreconciled Component Diff</span>
              <span className={`px-2 py-0.5 rounded font-bold ${
                summary.reconciliation.unreconciled_component_difference !== 0 
                  ? 'bg-critical/10 text-critical border border-critical/20 animate-pulse' 
                  : 'bg-healthy/10 text-healthy border border-healthy/20'
              }`}>
                {formatCurrency(summary.reconciliation.unreconciled_component_difference)}
              </span>
            </div>
            <div className="py-2 flex justify-between">
              <span className="text-muted-foreground">Net Payroll (Paid)</span>
              <span className="font-bold text-healthy">{formatCurrency(summary.reconciliation.net_payroll)}</span>
            </div>
            <div className="py-2 flex justify-between">
              <span className="text-muted-foreground">Gross minus Deductions</span>
              <span className="font-semibold text-foreground">{formatCurrency(summary.reconciliation.gross_minus_deductions)}</span>
            </div>
            <div className="py-2 flex justify-between items-center">
              <span className="text-muted-foreground">Net Unreconciled Diff</span>
              <span className={`px-2 py-0.5 rounded font-bold ${
                summary.reconciliation.net_unreconciled_difference !== 0 
                  ? 'bg-critical/10 text-critical border border-critical/20 animate-pulse' 
                  : 'bg-healthy/10 text-healthy border border-healthy/20'
              }`}>
                {formatCurrency(summary.reconciliation.net_unreconciled_difference)}
              </span>
            </div>
            <div className="py-2 flex justify-between">
              <span className="text-muted-foreground">Project Payroll Total Sum</span>
              <span className="font-semibold text-foreground">{formatCurrency(summary.reconciliation.project_payroll_total)}</span>
            </div>
            <div className="py-2 flex justify-between">
              <span className="text-muted-foreground">Dept Payroll Total Sum</span>
              <span className="font-semibold text-foreground">{formatCurrency(summary.reconciliation.department_payroll_total)}</span>
            </div>
            <div className="py-2 flex justify-between">
              <span className="text-muted-foreground">Employees Paid Count</span>
              <span className="font-bold text-foreground">{formatNumber(summary.reconciliation.employees_paid_count)}</span>
            </div>
            <div className="py-2 flex justify-between">
              <span className="text-muted-foreground">Payroll Exception Count</span>
              <span className="font-bold text-critical bg-critical/5 px-2 py-0.5 rounded border border-critical/10">{summary.reconciliation.payroll_exception_count}</span>
            </div>
          </div>
        </div>

        {/* Exceptions Table Card */}
        <div className="lg:col-span-2 space-y-3">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-foreground">Payroll Exceptions & Anomalies</h3>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Audit logs tracking payroll component mismatches, net pay discrepancies, and missing attributes.
            </p>
          </div>
          <ExceptionTable data={exceptions} />
        </div>
      </div>
    </div>
  );
};

export default Payroll;
