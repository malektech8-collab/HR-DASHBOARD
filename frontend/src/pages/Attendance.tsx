import React, { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { 
  fetchAttendanceSummary, 
  fetchAttendanceTrends, 
  fetchAttendanceByProject, 
  fetchAttendanceByDepartment, 
  fetchAttendanceLateArrival, 
  fetchAttendanceOvertime, 
  fetchAttendanceMissingPunches, 
  fetchAttendanceExceptions 
} from '../lib/api';
import type { 
  AttendanceSummaryData, 
  AttendanceTrendsData, 
  AttendanceByProjectData, 
  AttendanceByDepartmentData, 
  AttendanceLateArrivalData, 
  AttendanceOvertimeData, 
  AttendanceMissingPunchesData, 
  DQExceptionItem 
} from '../lib/types';
import { KpiCard } from '../components/cards/KpiCard';
import { ExceptionTable } from '../components/tables/ExceptionTable';
import { Sparkles, ShieldAlert, Clock } from 'lucide-react';
import { formatCurrency, formatPercent } from '../lib/formatters';

export const Attendance: React.FC = () => {
  const [summary, setSummary] = useState<AttendanceSummaryData | null>(null);
  const [trends, setTrends] = useState<AttendanceTrendsData | null>(null);
  const [projects, setProjects] = useState<AttendanceByProjectData | null>(null);
  const [departments, setDepartments] = useState<AttendanceByDepartmentData | null>(null);
  const [lateArrivals, setLateArrivals] = useState<AttendanceLateArrivalData | null>(null);
  const [overtime, setOvertime] = useState<AttendanceOvertimeData | null>(null);
  const [missingPunches, setMissingPunches] = useState<AttendanceMissingPunchesData | null>(null);
  const [exceptions, setExceptions] = useState<DQExceptionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [sumData, trData, projData, deptData, lateData, otData, mpData, excData] = await Promise.all([
          fetchAttendanceSummary(),
          fetchAttendanceTrends(),
          fetchAttendanceByProject(),
          fetchAttendanceByDepartment(),
          fetchAttendanceLateArrival(),
          fetchAttendanceOvertime(),
          fetchAttendanceMissingPunches(),
          fetchAttendanceExceptions()
        ]);
        setSummary(sumData);
        setTrends(trData);
        setProjects(projData);
        setDepartments(deptData);
        setLateArrivals(lateData);
        setOvertime(otData);
        setMissingPunches(mpData);
        setExceptions(excData.exceptions);
      } catch (err: any) {
        console.error(err);
        setError(err.message || 'Failed to load attendance dashboard data');
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
        <p className="text-sm font-semibold tracking-wide">Loading Attendance Dashboard...</p>
      </div>
    );
  }

  if (error || !summary || !trends || !projects || !departments || !lateArrivals || !overtime || !missingPunches) {
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
      unit: '',
      status: 'neutral' as const
    };
  }

  // ECharts Options
  
  // Row 3: Compliance Trend
  const complianceTrendOption = {
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
            <div style="font-weight: 700; color: #10b981;">Compliance: ${formatPercent(item.value)}</div>
          </div>
        `;
      }
    },
    grid: { top: '15%', left: '3%', right: '4%', bottom: '5%', containLabel: true },
    xAxis: {
      type: 'category',
      data: trends.trends.map(t => t.month),
      axisLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', fontSize: 11, fontFamily: 'Inter, sans-serif' }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      splitLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', fontSize: 11, fontFamily: 'Inter, sans-serif', formatter: '{value}%' }
    },
    series: [
      {
        name: 'Attendance Compliance %',
        data: trends.trends.map(t => t.attendance_compliance_pct),
        type: 'line',
        smooth: true,
        symbolSize: 6,
        itemStyle: { color: '#10b981' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(16, 185, 129, 0.2)' },
              { offset: 1, color: 'rgba(16, 185, 129, 0.0)' }
            ]
          }
        },
        lineStyle: { width: 3 }
      }
    ]
  };

  // Row 3: Absence Days Trend
  const absenceTrendOption = {
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
            <div style="font-weight: 700; color: #ef4444;">Absence: ${item.value} Days</div>
          </div>
        `;
      }
    },
    grid: { top: '15%', left: '3%', right: '4%', bottom: '5%', containLabel: true },
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
        name: 'Absence Days',
        data: trends.trends.map(t => t.absence_days),
        type: 'line',
        smooth: true,
        symbolSize: 6,
        itemStyle: { color: '#ef4444' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(239, 68, 68, 0.2)' },
              { offset: 1, color: 'rgba(239, 68, 68, 0.0)' }
            ]
          }
        },
        lineStyle: { width: 3 }
      }
    ]
  };

  // Row 4: Late Minutes by Project
  const lateMinutesProjectOption = {
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
            <div style="font-weight: 700; color: #f59e0b;">Late: ${item.value} Minutes</div>
          </div>
        `;
      }
    },
    grid: { top: '15%', left: '3%', right: '4%', bottom: '5%', containLabel: true },
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
        name: 'Late Minutes',
        data: projects.projects.map(p => p.late_minutes),
        type: 'bar',
        barWidth: '35%',
        itemStyle: {
          color: '#f59e0b',
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  };

  // Row 4: Net Late Minutes by Department
  const netLateDepartmentOption = {
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
            <div style="font-weight: 700; color: #3b82f6;">Net Late: ${item.value} Minutes</div>
          </div>
        `;
      }
    },
    grid: { top: '15%', left: '3%', right: '4%', bottom: '5%', containLabel: true },
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
        name: 'Net Late Minutes',
        data: departments.departments.map(d => d.net_late_minutes),
        type: 'bar',
        barWidth: '35%',
        itemStyle: {
          color: '#3b82f6',
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  };

  // Row 5: Missing Punches by Project
  const missingPunchesOption = {
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
            <div style="font-weight: 700; color: #ec4899;">Punches Missing: ${item.value}</div>
          </div>
        `;
      }
    },
    grid: { top: '15%', left: '3%', right: '4%', bottom: '5%', containLabel: true },
    xAxis: {
      type: 'category',
      data: projects.projects.map(p => p.project),
      axisLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', fontSize: 10, fontFamily: 'Inter, sans-serif' }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', fontSize: 10, fontFamily: 'Inter, sans-serif' }
    },
    series: [
      {
        name: 'Missing Punches',
        data: projects.projects.map(p => p.missing_punches),
        type: 'bar',
        barWidth: '40%',
        itemStyle: {
          color: '#ec4899',
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  };

  // Row 5: Overtime Hours by Project
  const overtimeHoursOption = {
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
            <div style="font-weight: 700; color: #8b5cf6;">OT: ${item.value} Hours</div>
          </div>
        `;
      }
    },
    grid: { top: '15%', left: '3%', right: '4%', bottom: '5%', containLabel: true },
    xAxis: {
      type: 'category',
      data: projects.projects.map(p => p.project),
      axisLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', fontSize: 10, fontFamily: 'Inter, sans-serif' }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', fontSize: 10, fontFamily: 'Inter, sans-serif' }
    },
    series: [
      {
        name: 'Overtime Hours',
        data: projects.projects.map(p => p.overtime_hours),
        type: 'bar',
        barWidth: '40%',
        itemStyle: {
          color: '#8b5cf6',
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  };

  // Row 5: Overtime Cost by Project
  const overtimeCostOption = {
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
            <div style="font-weight: 700; color: #14b8a6;">OT Cost: ${formatCurrency(item.value)}</div>
          </div>
        `;
      }
    },
    grid: { top: '15%', left: '3%', right: '4%', bottom: '5%', containLabel: true },
    xAxis: {
      type: 'category',
      data: projects.projects.map(p => p.project),
      axisLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', fontSize: 10, fontFamily: 'Inter, sans-serif' }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#1e293b' } },
      axisLabel: { color: '#64748b', fontSize: 10, fontFamily: 'Inter, sans-serif' }
    },
    series: [
      {
        name: 'Overtime Cost',
        data: projects.projects.map(p => p.overtime_cost),
        type: 'bar',
        barWidth: '40%',
        itemStyle: {
          color: '#14b8a6',
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  };

  const compKpi = getKpi("attendance_compliance_pct");
  const absKpi = getKpi("absence_days");
  const lateKpi = getKpi("late_minutes");
  const excusedKpi = getKpi("excused_late_minutes");
  const netKpi = getKpi("net_late_minutes");
  const earlyKpi = getKpi("early_leave_minutes");
  const punchKpi = getKpi("missing_punch_count");
  const otHoursKpi = getKpi("overtime_hours");
  const otCostKpi = getKpi("overtime_cost");
  const excCountKpi = getKpi("attendance_exception_count");

  return (
    <div className="space-y-6">
      {/* Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Attendance & Absence Command Center</h1>
            <div className="flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-primary/10 border border-primary/20 text-xs font-semibold text-primary">
              <Sparkles className="w-3 h-3" /> MVP Mode
            </div>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Official attendance metrics, net lateness parameters, approved overtime audit logs, and reconciliation status.
          </p>
        </div>
        <div className="flex items-center gap-3 bg-muted/30 border border-border px-4 py-2 rounded-xl text-xs font-medium text-foreground self-start md:self-auto">
          <Clock className="w-4 h-4 text-primary" />
          <span>Report Month: <span className="font-bold text-primary">{summary.report_month}</span></span>
        </div>
      </div>

      {/* Row 1: KPI Cards 1-5 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <KpiCard
          label={compKpi.label}
          value={compKpi.value}
          unit={compKpi.unit}
          status={compKpi.status}
        />
        <KpiCard
          label={absKpi.label}
          value={absKpi.value}
          unit={absKpi.unit}
          status={absKpi.status}
        />
        <KpiCard
          label={lateKpi.label}
          value={lateKpi.value}
          unit={lateKpi.unit}
          status={lateKpi.status}
        />
        <KpiCard
          label={excusedKpi.label}
          value={excusedKpi.value}
          unit={excusedKpi.unit}
          status={excusedKpi.status}
        />
        <KpiCard
          label={netKpi.label}
          value={netKpi.value}
          unit={netKpi.unit}
          status={netKpi.status}
        />
      </div>

      {/* Row 2: KPI Cards 6-10 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <KpiCard
          label={earlyKpi.label}
          value={earlyKpi.value}
          unit={earlyKpi.unit}
          status={earlyKpi.status}
        />
        <KpiCard
          label={punchKpi.label}
          value={punchKpi.value}
          unit={punchKpi.unit}
          status={punchKpi.status}
        />
        <KpiCard
          label={otHoursKpi.label}
          value={otHoursKpi.value}
          unit={otHoursKpi.unit}
          status={otHoursKpi.status}
        />
        <KpiCard
          label={otCostKpi.label}
          value={otCostKpi.value}
          unit={otCostKpi.unit}
          status={otCostKpi.status}
        />
        <KpiCard
          label={excCountKpi.label}
          value={excCountKpi.value}
          unit={excCountKpi.unit}
          status={excCountKpi.status}
        />
      </div>

      {/* Row 3: ECharts Trends */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card border border-border rounded-xl p-5 shadow-md flex flex-col justify-between">
          <div className="flex items-center justify-between pb-3 border-b border-border/50">
            <span className="text-sm font-semibold tracking-wide text-foreground">Attendance Compliance Trend</span>
            <span className="text-xs text-muted-foreground">Historical Compliance Rate</span>
          </div>
          <div className="h-64 mt-4">
            <ReactECharts option={complianceTrendOption} style={{ height: '100%' }} />
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-5 shadow-md flex flex-col justify-between">
          <div className="flex items-center justify-between pb-3 border-b border-border/50">
            <span className="text-sm font-semibold tracking-wide text-foreground">Absence Days Trend</span>
            <span className="text-xs text-muted-foreground">Historical Absence Count</span>
          </div>
          <div className="h-64 mt-4">
            <ReactECharts option={absenceTrendOption} style={{ height: '100%' }} />
          </div>
        </div>
      </div>

      {/* Row 4: ECharts Project & Department Lateness */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card border border-border rounded-xl p-5 shadow-md flex flex-col justify-between">
          <div className="flex items-center justify-between pb-3 border-b border-border/50">
            <span className="text-sm font-semibold tracking-wide text-foreground">Late Minutes by Project</span>
            <span className="text-xs text-muted-foreground">Sum of Lateness Delay</span>
          </div>
          <div className="h-64 mt-4">
            <ReactECharts option={lateMinutesProjectOption} style={{ height: '100%' }} />
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-5 shadow-md flex flex-col justify-between">
          <div className="flex items-center justify-between pb-3 border-b border-border/50">
            <span className="text-sm font-semibold tracking-wide text-foreground">Net Late Minutes by Department</span>
            <span className="text-xs text-muted-foreground">Total Excused Subtracted</span>
          </div>
          <div className="h-64 mt-4">
            <ReactECharts option={netLateDepartmentOption} style={{ height: '100%' }} />
          </div>
        </div>
      </div>

      {/* Row 5: 3-Column ECharts Bar Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-card border border-border rounded-xl p-5 shadow-md flex flex-col justify-between">
          <div className="flex items-center justify-between pb-3 border-b border-border/50">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Missing Punches by Project</span>
          </div>
          <div className="h-56 mt-4">
            <ReactECharts option={missingPunchesOption} style={{ height: '100%' }} />
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-5 shadow-md flex flex-col justify-between">
          <div className="flex items-center justify-between pb-3 border-b border-border/50">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Overtime Hours by Project</span>
          </div>
          <div className="h-56 mt-4">
            <ReactECharts option={overtimeHoursOption} style={{ height: '100%' }} />
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-5 shadow-md flex flex-col justify-between">
          <div className="flex items-center justify-between pb-3 border-b border-border/50">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Overtime Cost by Project</span>
          </div>
          <div className="h-56 mt-4">
            <ReactECharts option={overtimeCostOption} style={{ height: '100%' }} />
          </div>
        </div>
      </div>

      {/* Row 6: Exceptions Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold tracking-tight text-foreground">Attendance Audit & Exceptions Log</h2>
          <span className="text-xs text-muted-foreground">Reconciled to expected workdays denominator</span>
        </div>
        <ExceptionTable data={exceptions} />
      </div>
    </div>
  );
};

export default Attendance;
