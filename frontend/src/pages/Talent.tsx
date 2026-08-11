import React, { useEffect, useState } from 'react';
import ReactECharts from '../components/charts/ReactECharts';
import {
  fetchTalentSummary,
  fetchPerformanceDistribution,
  fetchPerformanceTrends,
  fetchPerformanceByProject,
  fetchPerformanceByDepartment,
  fetchGoalCompletion,
  fetchCompetencyGaps,
  fetchLearningCompletion,
  fetchSuccessionCoverage,
  fetchSuccessorReadiness,
  fetchTalentRisk,
  fetchTalentExceptions,
} from '../lib/api';
import type {
  TalentSummaryData,
  PerformanceDistributionData,
  PerformanceTrendsData,
  PerformanceByProjectData,
  PerformanceByDepartmentData,
  GoalCompletionData,
  CompetencyGapData,
  LearningCompletionData,
  SuccessionCoverageData,
  SuccessorReadinessData,
  TalentRiskData,
  DQExceptionItem,
} from '../lib/types';
import { KpiCard } from '../components/cards/KpiCard';
import { ExceptionTable } from '../components/tables/ExceptionTable';
import { Star, AlertTriangle } from 'lucide-react';
import { NotProvided, collectSuppressions } from '../components/ui/NotProvided';

const CATEGORY_COLORS: Record<string, string> = {
  'Outstanding': '#10b981',
  'Exceeds Expectations': '#6366f1',
  'Meets Expectations': '#f59e0b',
  'Needs Improvement': '#f97316',
  'Unsatisfactory': '#ef4444',
};

const RISK_COLORS: Record<string, string> = {
  'High Risk': '#ef4444',
  'Medium Risk': '#f59e0b',
  'Low Risk': '#10b981',
};

const READINESS_COLORS: Record<string, string> = {
  'Ready Now': '#10b981',
  '1 Year': '#6366f1',
  '2 Years': '#f59e0b',
  'Missing': '#6b7280',
};

export const Talent: React.FC = () => {
  const [summary, setSummary] = useState<TalentSummaryData | null>(null);
  const [distribution, setDistribution] = useState<PerformanceDistributionData | null>(null);
  const [trends, setTrends] = useState<PerformanceTrendsData | null>(null);
  const [byProject, setByProject] = useState<PerformanceByProjectData | null>(null);
  const [byDepartment, setByDepartment] = useState<PerformanceByDepartmentData | null>(null);
  const [goals, setGoals] = useState<GoalCompletionData | null>(null);
  const [competencyGaps, setCompetencyGaps] = useState<CompetencyGapData | null>(null);
  const [learning, setLearning] = useState<LearningCompletionData | null>(null);
  const [succession, setSuccession] = useState<SuccessionCoverageData | null>(null);
  const [readiness, setReadiness] = useState<SuccessorReadinessData | null>(null);
  const [riskData, setRiskData] = useState<TalentRiskData | null>(null);
  const [exceptions, setExceptions] = useState<DQExceptionItem[] | null>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [
        sumRes, distRes, trendRes, projRes, deptRes,
        goalRes, compRes, learnRes, succRes, readRes, riskRes, excRes
      ] = await Promise.all([
        fetchTalentSummary(),
        fetchPerformanceDistribution(),
        fetchPerformanceTrends(),
        fetchPerformanceByProject(),
        fetchPerformanceByDepartment(),
        fetchGoalCompletion(),
        fetchCompetencyGaps(),
        fetchLearningCompletion(),
        fetchSuccessionCoverage(),
        fetchSuccessorReadiness(),
        fetchTalentRisk(),
        fetchTalentExceptions(),
      ]);

      setSummary(sumRes);
      setDistribution(distRes);
      setTrends(trendRes);
      setByProject(projRes);
      setByDepartment(deptRes);
      setGoals(goalRes);
      setCompetencyGaps(compRes);
      setLearning(learnRes);
      setSuccession(succRes);
      setReadiness(readRes);
      setRiskData(riskRes);
      setExceptions(excRes.exceptions);
    } catch (err: any) {
      console.error('Error loading Talent page data:', err);
      setError(err.message || 'Failed to load talent data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-center">
        <AlertTriangle className="mx-auto h-12 w-12 text-critical mb-4" />
        <p className="text-critical text-lg font-semibold">{error}</p>
        <button onClick={loadData} className="mt-4 px-4 py-2 bg-accent rounded-lg text-white hover:bg-accent-hover transition">Retry</button>
      </div>
    );
  }

  // Step 2b: a null container means the client has not provided that
  // domain. Bind, then guard - the compiler narrows these for the
  // whole render, so nothing below can draw a zero in their place.
  const byDepartmentDepartmentsRows = byDepartment?.departments;
  const byProjectProjectsRows = byProject?.projects;
  const competencyGapsGapsRows = competencyGaps?.gaps;
  const distributionDistributionRows = distribution?.distribution;
  const goalsGoalsRows = goals?.goals;
  const learningCompletionRows = learning?.completion;
  const readinessReadinessRows = readiness?.readiness;
  const riskDataRisksRows = riskData?.risks;
  const successionCoverageRows = succession?.coverage;
  const summaryKpisRows = summary?.kpis;
  const trendsTrendsRows = trends?.trends;
  if (!byDepartmentDepartmentsRows || !byProjectProjectsRows || !competencyGapsGapsRows || !distributionDistributionRows || !goalsGoalsRows || !learningCompletionRows || !readinessReadinessRows || !riskDataRisksRows || !successionCoverageRows || !summaryKpisRows || !trendsTrendsRows || !exceptions) {
    return (
      <NotProvided
        title="Talent"
        items={collectSuppressions(byDepartment, byProject, competencyGaps, distribution, goals, learning, readiness, riskData, succession, summary, trends)}
      />
    );
  }

  // ---- KPI lookups ----
  const getKpi = (key: string) => summaryKpisRows.find(k => k.key === key);

  const kpiKeys = [
    'employees_reviewed', 'review_completion_pct', 'average_performance_rating',
    'high_performers', 'low_performers', 'goal_completion_pct',
    'training_completion_pct', 'average_training_hours',
    'critical_roles_covered_pct', 'ready_successors', 'talent_exception_count',
  ];

  // ---- Chart: Performance Distribution ----
  const distCategories = distributionDistributionRows.map(d => d.performance_category) || [];
  const distValues = distributionDistributionRows.map(d => d.employee_count) || [];
  const distColors = distCategories.map(c => CATEGORY_COLORS[c] || '#6366f1');

  const distOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: {
      orient: 'vertical', right: '2%', top: 'center',
      textStyle: { color: '#94a3b8', fontSize: 11 },
    },
    series: [{
      type: 'pie', radius: ['45%', '70%'], center: ['38%', '50%'],
      data: distCategories.map((cat, i) => ({
        name: cat, value: distValues[i],
        itemStyle: { color: distColors[i] },
      })),
      label: { show: false },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } },
    }],
  };

  // ---- Chart: Review Trend ----
  const trendPeriods = trendsTrendsRows.map(t => t.period) || [];
  const trendRatings = trendsTrendsRows.map(t => t.avg_rating) || [];
  const trendPcts = trendsTrendsRows.map(t => t.completion_pct) || [];

  const trendOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['Avg Rating', 'Completion %'], textStyle: { color: '#94a3b8' }, top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: trendPeriods, axisLabel: { color: '#64748b' }, axisLine: { lineStyle: { color: '#334155' } } },
    yAxis: [
      { type: 'value', name: 'Rating', min: 0, max: 5, axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: '#1e293b' } } },
      { type: 'value', name: '%', min: 0, max: 100, axisLabel: { color: '#64748b' } },
    ],
    series: [
      { name: 'Avg Rating', type: 'line', data: trendRatings, smooth: true, itemStyle: { color: '#6366f1' }, areaStyle: { opacity: 0.15 } },
      { name: 'Completion %', type: 'bar', yAxisIndex: 1, data: trendPcts, itemStyle: { color: '#10b981', opacity: 0.8 } },
    ],
  };

  // ---- Chart: Performance by Department ----
  const deptNames = byDepartmentDepartmentsRows.map(d => d.department) || [];
  const deptHigh = byDepartmentDepartmentsRows.map(d => d.high_performers) || [];
  const deptLow = byDepartmentDepartmentsRows.map(d => d.low_performers) || [];


  const deptOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['High Performers', 'Low Performers'], textStyle: { color: '#94a3b8' }, top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: deptNames, axisLabel: { color: '#64748b', rotate: 20 }, axisLine: { lineStyle: { color: '#334155' } } },
    yAxis: { type: 'value', axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: '#1e293b' } } },
    series: [
      { name: 'High Performers', type: 'bar', stack: 'total', data: deptHigh, itemStyle: { color: '#6366f1' } },
      { name: 'Low Performers', type: 'bar', stack: 'total', data: deptLow, itemStyle: { color: '#ef4444' } },
    ],
  };

  // ---- Chart: Goal Completion by Department ----
  const goalDepts = goalsGoalsRows.map(g => g.department) || [];
  const goalCompleted = goalsGoalsRows.map(g => g.completed_goals) || [];
  const goalOverdue = goalsGoalsRows.map(g => g.overdue_goals) || [];
  const goalInProgress = goalsGoalsRows.map(g => g.in_progress_goals) || [];

  const goalOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['Completed', 'In Progress', 'Overdue'], textStyle: { color: '#94a3b8' }, top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: goalDepts, axisLabel: { color: '#64748b', rotate: 20 }, axisLine: { lineStyle: { color: '#334155' } } },
    yAxis: { type: 'value', axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: '#1e293b' } } },
    series: [
      { name: 'Completed', type: 'bar', stack: 'goals', data: goalCompleted, itemStyle: { color: '#10b981' } },
      { name: 'In Progress', type: 'bar', stack: 'goals', data: goalInProgress, itemStyle: { color: '#f59e0b' } },
      { name: 'Overdue', type: 'bar', stack: 'goals', data: goalOverdue, itemStyle: { color: '#ef4444' } },
    ],
  };

  // ---- Chart: Competency Gaps ----
  const compNames = competencyGapsGapsRows.map(g => g.competency_name) || [];
  const compRequired = competencyGapsGapsRows.map(g => g.avg_required) || [];
  const compActual = competencyGapsGapsRows.map(g => g.avg_actual) || [];

  const compOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['Required', 'Actual'], textStyle: { color: '#94a3b8' }, top: 0 },
    grid: { left: '15%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value', max: 5, axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: '#1e293b' } } },
    yAxis: { type: 'category', data: compNames, axisLabel: { color: '#64748b', fontSize: 11 } },
    series: [
      { name: 'Required', type: 'bar', data: compRequired, itemStyle: { color: '#475569' }, barMaxWidth: 16 },
      { name: 'Actual', type: 'bar', data: compActual, itemStyle: { color: '#6366f1' }, barMaxWidth: 16 },
    ],
  };

  // ---- Chart: Learning by Category ----
  const learnCats = learningCompletionRows.map(l => l.category) || [];
  const learnCompleted = learningCompletionRows.map(l => l.completed_enrollments) || [];
  const learnTotal = learningCompletionRows.map(l => l.eligible_enrollments) || [];
  const learnHours = learningCompletionRows.map(l => l.total_hours) || [];

  const learnOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['Completed', 'Eligible', 'Total Hours'], textStyle: { color: '#94a3b8' }, top: 0 },
    grid: { left: '3%', right: '8%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: learnCats, axisLabel: { color: '#64748b', rotate: 15 }, axisLine: { lineStyle: { color: '#334155' } } },
    yAxis: [
      { type: 'value', name: 'Enrollments', axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: '#1e293b' } } },
      { type: 'value', name: 'Hours', axisLabel: { color: '#64748b' } },
    ],
    series: [
      { name: 'Completed', type: 'bar', stack: 'enr', data: learnCompleted, itemStyle: { color: '#10b981' } },
      { name: 'Eligible', type: 'bar', stack: 'enr', data: learnTotal.map((t, i) => t - learnCompleted[i]), itemStyle: { color: '#334155' } },
      { name: 'Total Hours', type: 'line', yAxisIndex: 1, data: learnHours, smooth: true, itemStyle: { color: '#f59e0b' } },
    ],
  };

  // ---- Chart: Successor Readiness ----
  const readLabels = readinessReadinessRows.map(r => r.readiness) || [];
  const readCounts = readinessReadinessRows.map(r => r.successor_count) || [];

  const readOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', right: '2%', top: 'center', textStyle: { color: '#94a3b8', fontSize: 11 } },
    series: [{
      type: 'pie', radius: ['45%', '70%'], center: ['40%', '50%'],
      data: readLabels.map((label, i) => ({
        name: label, value: readCounts[i],
        itemStyle: { color: READINESS_COLORS[label] || '#6366f1' },
      })),
      label: { show: false },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } },
    }],
  };

  // ---- Chart: Talent Risk Distribution ----
  const riskSummary = riskDataRisksRows.reduce<Record<string, number>>((acc, r) => {
    acc[r.risk_category] = (acc[r.risk_category] || 0) + 1;
    return acc;
  }, {}) || {};
  const riskLabels = Object.keys(riskSummary);
  const riskCounts = riskLabels.map(k => riskSummary[k]);

  const riskOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', right: '2%', top: 'center', textStyle: { color: '#94a3b8', fontSize: 11 } },
    series: [{
      type: 'pie', radius: ['45%', '70%'], center: ['40%', '50%'],
      data: riskLabels.map((label, i) => ({
        name: label, value: riskCounts[i],
        itemStyle: { color: RISK_COLORS[label] || '#6b7280' },
      })),
      label: { show: false },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } },
    }],
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Talent, Performance & Succession</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Report Month: <span className="text-accent font-medium">{summary?.report_month || '—'}</span>
          </p>
        </div>
        <button
          id="talent-refresh-btn"
          onClick={loadData}
          className="flex items-center gap-2 px-4 py-2 bg-accent rounded-lg text-white text-sm hover:bg-accent-hover transition"
        >
          <Star size={16} /> Refresh
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
        {kpiKeys.map(key => {
          const kpi = getKpi(key);
          if (!kpi) return null;
          return (
            <KpiCard
              key={key}
              label={kpi.label}
              value={kpi.value}
              unit={kpi.unit}
              status={kpi.status as any}
            />
          );
        })}
      </div>

      {/* Row 1: Performance Distribution + Trend */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="bg-card border border-border rounded-xl p-5 transition-theme">
          <h2 className="text-foreground font-semibold text-base mb-4">Performance Distribution</h2>
          {distribution && distributionDistributionRows.length > 0
            ? <ReactECharts option={distOption} style={{ height: 260 }} />
            : <p className="text-muted-foreground text-sm text-center py-16">No data available</p>
          }
        </div>
        <div className="bg-card border border-border rounded-xl p-5 transition-theme">
          <h2 className="text-foreground font-semibold text-base mb-4">Review Completion Trend</h2>
          {trends && trendsTrendsRows.length > 0
            ? <ReactECharts option={trendOption} style={{ height: 260 }} />
            : <p className="text-muted-foreground text-sm text-center py-16">No data available</p>
          }
        </div>
      </div>

      {/* Row 2: Performance by Department + Goal Completion */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="bg-card border border-border rounded-xl p-5 transition-theme">
          <h2 className="text-foreground font-semibold text-base mb-4">Performance by Department</h2>
          {byDepartment && byDepartmentDepartmentsRows.length > 0
            ? <ReactECharts option={deptOption} style={{ height: 260 }} />
            : <p className="text-muted-foreground text-sm text-center py-16">No data available</p>
          }
        </div>
        <div className="bg-card border border-border rounded-xl p-5 transition-theme">
          <h2 className="text-foreground font-semibold text-base mb-4">Goal Completion by Department</h2>
          {goals && goalsGoalsRows.length > 0
            ? <ReactECharts option={goalOption} style={{ height: 260 }} />
            : <p className="text-muted-foreground text-sm text-center py-16">No data available</p>
          }
        </div>
      </div>

      {/* Row 3: Competency Gaps + Learning Completion */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="bg-card border border-border rounded-xl p-5 transition-theme">
          <h2 className="text-foreground font-semibold text-base mb-4">Competency Gaps</h2>
          {competencyGaps && competencyGapsGapsRows.length > 0
            ? <ReactECharts option={compOption} style={{ height: 280 }} />
            : <p className="text-muted-foreground text-sm text-center py-16">No data available</p>
          }
        </div>
        <div className="bg-card border border-border rounded-xl p-5 transition-theme">
          <h2 className="text-foreground font-semibold text-base mb-4">Learning Completion by Category</h2>
          {learning && learningCompletionRows.length > 0
            ? <ReactECharts option={learnOption} style={{ height: 280 }} />
            : <p className="text-muted-foreground text-sm text-center py-16">No data available</p>
          }
        </div>
      </div>

      {/* Row 4: Succession Coverage Table */}
      <div className="bg-card border border-border rounded-xl p-5 transition-theme">
        <h2 className="text-foreground font-semibold text-base mb-4">Succession Plan Coverage — Critical Roles</h2>
        {succession && successionCoverageRows.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left text-muted-foreground font-medium py-2 px-3">Role</th>
                  <th className="text-right text-muted-foreground font-medium py-2 px-3">Valid Successors</th>
                  <th className="text-center text-muted-foreground font-medium py-2 px-3">Coverage</th>
                </tr>
              </thead>
              <tbody>
                {successionCoverageRows.map((row, i) => (
                  <tr key={i} className="border-b border-border/60 hover:bg-muted/50 transition">
                    <td className="py-2 px-3 text-foreground">{row.role_title}</td>
                    <td className="py-2 px-3 text-right text-muted-foreground">{row.valid_successor_count}</td>
                    <td className="py-2 px-3 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        row.coverage_status === 'Covered'
                          ? 'bg-healthy/20 text-healthy'
                          : 'bg-critical/20 text-critical'
                      }`}>
                        {row.coverage_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-muted-foreground text-sm text-center py-8">No succession data available</p>
        )}
      </div>

      {/* Row 5: Readiness + Risk */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="bg-card border border-border rounded-xl p-5 transition-theme">
          <h2 className="text-foreground font-semibold text-base mb-4">Successor Readiness</h2>
          {readiness && readinessReadinessRows.length > 0
            ? <ReactECharts option={readOption} style={{ height: 240 }} />
            : <p className="text-muted-foreground text-sm text-center py-16">No data available</p>
          }
        </div>
        <div className="bg-card border border-border rounded-xl p-5 transition-theme">
          <h2 className="text-foreground font-semibold text-base mb-4">Talent Risk Profile</h2>
          {riskData && riskDataRisksRows.length > 0
            ? <ReactECharts option={riskOption} style={{ height: 240 }} />
            : <p className="text-muted-foreground text-sm text-center py-16">No data available</p>
          }
        </div>
      </div>

      {/* Performance by Project Table */}
      <div className="bg-card border border-border rounded-xl p-5 transition-theme">
        <h2 className="text-foreground font-semibold text-base mb-4">Performance by Project</h2>
        {byProject && byProjectProjectsRows.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left text-muted-foreground font-medium py-2 px-3">Project</th>
                  <th className="text-right text-muted-foreground font-medium py-2 px-3">Reviewed</th>
                  <th className="text-right text-muted-foreground font-medium py-2 px-3">Avg Rating</th>
                  <th className="text-right text-muted-foreground font-medium py-2 px-3">High Performers</th>
                  <th className="text-right text-muted-foreground font-medium py-2 px-3">Low Performers</th>
                </tr>
              </thead>
              <tbody>
                {byProjectProjectsRows.map((row, i) => (
                  <tr key={i} className="border-b border-border/60 hover:bg-muted/50 transition">
                    <td className="py-2 px-3 text-foreground">{row.project}</td>
                    <td className="py-2 px-3 text-right text-muted-foreground">{row.reviewed_count}</td>
                    <td className="py-2 px-3 text-right">
                      <span className={`font-semibold ${row.average_rating >= 3.5 ? 'text-healthy' : row.average_rating >= 2.5 ? 'text-warning' : 'text-critical'}`}>
                        {row.average_rating.toFixed(2)}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-right text-accent">{row.high_performers}</td>
                    <td className="py-2 px-3 text-right text-critical">{row.low_performers}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-muted-foreground text-sm text-center py-8">No project data available</p>
        )}
      </div>

      {/* Talent Exceptions Table */}
      <div className="bg-card border border-border rounded-xl p-5 transition-theme">
        <h2 className="text-foreground font-semibold text-base mb-4">
          Talent Data Quality Exceptions
          <span className="ml-2 bg-critical/20 text-critical border border-critical/30 text-xs px-2 py-0.5 rounded">
            {exceptions.length}
          </span>
        </h2>
        <ExceptionTable
          data={exceptions}
        />
      </div>
    </div>
  );
};
