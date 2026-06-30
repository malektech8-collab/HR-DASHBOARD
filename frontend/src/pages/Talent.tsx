import React, { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
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
  const [exceptions, setExceptions] = useState<DQExceptionItem[]>([]);
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
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-center">
        <AlertTriangle className="mx-auto h-12 w-12 text-red-400 mb-4" />
        <p className="text-red-400 text-lg font-semibold">{error}</p>
        <button onClick={loadData} className="mt-4 px-4 py-2 bg-indigo-600 rounded-lg text-white hover:bg-indigo-500 transition">Retry</button>
      </div>
    );
  }

  // ---- KPI lookups ----
  const getKpi = (key: string) => summary?.kpis.find(k => k.key === key);

  const kpiKeys = [
    'employees_reviewed', 'review_completion_pct', 'average_performance_rating',
    'high_performers', 'low_performers', 'goal_completion_pct',
    'training_completion_pct', 'average_training_hours',
    'critical_roles_covered_pct', 'ready_successors', 'talent_exception_count',
  ];

  // ---- Chart: Performance Distribution ----
  const distCategories = distribution?.distribution.map(d => d.performance_category) || [];
  const distValues = distribution?.distribution.map(d => d.employee_count) || [];
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
  const trendPeriods = trends?.trends.map(t => t.period) || [];
  const trendRatings = trends?.trends.map(t => t.avg_rating) || [];
  const trendPcts = trends?.trends.map(t => t.completion_pct) || [];

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
  const deptNames = byDepartment?.departments.map(d => d.department) || [];
  const deptHigh = byDepartment?.departments.map(d => d.high_performers) || [];
  const deptLow = byDepartment?.departments.map(d => d.low_performers) || [];


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
  const goalDepts = goals?.goals.map(g => g.department) || [];
  const goalCompleted = goals?.goals.map(g => g.completed_goals) || [];
  const goalOverdue = goals?.goals.map(g => g.overdue_goals) || [];
  const goalInProgress = goals?.goals.map(g => g.in_progress_goals) || [];

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
  const compNames = competencyGaps?.gaps.map(g => g.competency_name) || [];
  const compRequired = competencyGaps?.gaps.map(g => g.avg_required) || [];
  const compActual = competencyGaps?.gaps.map(g => g.avg_actual) || [];

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
  const learnCats = learning?.completion.map(l => l.category) || [];
  const learnCompleted = learning?.completion.map(l => l.completed_enrollments) || [];
  const learnTotal = learning?.completion.map(l => l.eligible_enrollments) || [];
  const learnHours = learning?.completion.map(l => l.total_hours) || [];

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
  const readLabels = readiness?.readiness.map(r => r.readiness) || [];
  const readCounts = readiness?.readiness.map(r => r.successor_count) || [];

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
  const riskSummary = riskData?.risks.reduce<Record<string, number>>((acc, r) => {
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
          <h1 className="text-2xl font-bold text-white">Talent, Performance & Succession</h1>
          <p className="text-slate-400 text-sm mt-1">
            Report Month: <span className="text-indigo-400 font-medium">{summary?.report_month || '—'}</span>
          </p>
        </div>
        <button
          id="talent-refresh-btn"
          onClick={loadData}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 rounded-lg text-white text-sm hover:bg-indigo-500 transition"
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
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
          <h2 className="text-white font-semibold text-base mb-4">Performance Distribution</h2>
          {distribution && distribution.distribution.length > 0
            ? <ReactECharts option={distOption} style={{ height: 260 }} />
            : <p className="text-slate-400 text-sm text-center py-16">No data available</p>
          }
        </div>
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
          <h2 className="text-white font-semibold text-base mb-4">Review Completion Trend</h2>
          {trends && trends.trends.length > 0
            ? <ReactECharts option={trendOption} style={{ height: 260 }} />
            : <p className="text-slate-400 text-sm text-center py-16">No data available</p>
          }
        </div>
      </div>

      {/* Row 2: Performance by Department + Goal Completion */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
          <h2 className="text-white font-semibold text-base mb-4">Performance by Department</h2>
          {byDepartment && byDepartment.departments.length > 0
            ? <ReactECharts option={deptOption} style={{ height: 260 }} />
            : <p className="text-slate-400 text-sm text-center py-16">No data available</p>
          }
        </div>
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
          <h2 className="text-white font-semibold text-base mb-4">Goal Completion by Department</h2>
          {goals && goals.goals.length > 0
            ? <ReactECharts option={goalOption} style={{ height: 260 }} />
            : <p className="text-slate-400 text-sm text-center py-16">No data available</p>
          }
        </div>
      </div>

      {/* Row 3: Competency Gaps + Learning Completion */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
          <h2 className="text-white font-semibold text-base mb-4">Competency Gaps</h2>
          {competencyGaps && competencyGaps.gaps.length > 0
            ? <ReactECharts option={compOption} style={{ height: 280 }} />
            : <p className="text-slate-400 text-sm text-center py-16">No data available</p>
          }
        </div>
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
          <h2 className="text-white font-semibold text-base mb-4">Learning Completion by Category</h2>
          {learning && learning.completion.length > 0
            ? <ReactECharts option={learnOption} style={{ height: 280 }} />
            : <p className="text-slate-400 text-sm text-center py-16">No data available</p>
          }
        </div>
      </div>

      {/* Row 4: Succession Coverage Table */}
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
        <h2 className="text-white font-semibold text-base mb-4">Succession Plan Coverage — Critical Roles</h2>
        {succession && succession.coverage.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left text-slate-400 font-medium py-2 px-3">Role</th>
                  <th className="text-right text-slate-400 font-medium py-2 px-3">Valid Successors</th>
                  <th className="text-center text-slate-400 font-medium py-2 px-3">Coverage</th>
                </tr>
              </thead>
              <tbody>
                {succession.coverage.map((row, i) => (
                  <tr key={i} className="border-b border-slate-700/40 hover:bg-slate-700/30 transition">
                    <td className="py-2 px-3 text-slate-200">{row.role_title}</td>
                    <td className="py-2 px-3 text-right text-slate-300">{row.valid_successor_count}</td>
                    <td className="py-2 px-3 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        row.coverage_status === 'Covered'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : 'bg-red-500/20 text-red-400'
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
          <p className="text-slate-400 text-sm text-center py-8">No succession data available</p>
        )}
      </div>

      {/* Row 5: Readiness + Risk */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
          <h2 className="text-white font-semibold text-base mb-4">Successor Readiness</h2>
          {readiness && readiness.readiness.length > 0
            ? <ReactECharts option={readOption} style={{ height: 240 }} />
            : <p className="text-slate-400 text-sm text-center py-16">No data available</p>
          }
        </div>
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
          <h2 className="text-white font-semibold text-base mb-4">Talent Risk Profile</h2>
          {riskData && riskData.risks.length > 0
            ? <ReactECharts option={riskOption} style={{ height: 240 }} />
            : <p className="text-slate-400 text-sm text-center py-16">No data available</p>
          }
        </div>
      </div>

      {/* Performance by Project Table */}
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
        <h2 className="text-white font-semibold text-base mb-4">Performance by Project</h2>
        {byProject && byProject.projects.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left text-slate-400 font-medium py-2 px-3">Project</th>
                  <th className="text-right text-slate-400 font-medium py-2 px-3">Reviewed</th>
                  <th className="text-right text-slate-400 font-medium py-2 px-3">Avg Rating</th>
                  <th className="text-right text-slate-400 font-medium py-2 px-3">High Performers</th>
                  <th className="text-right text-slate-400 font-medium py-2 px-3">Low Performers</th>
                </tr>
              </thead>
              <tbody>
                {byProject.projects.map((row, i) => (
                  <tr key={i} className="border-b border-slate-700/40 hover:bg-slate-700/30 transition">
                    <td className="py-2 px-3 text-slate-200">{row.project}</td>
                    <td className="py-2 px-3 text-right text-slate-300">{row.reviewed_count}</td>
                    <td className="py-2 px-3 text-right">
                      <span className={`font-semibold ${row.average_rating >= 3.5 ? 'text-emerald-400' : row.average_rating >= 2.5 ? 'text-amber-400' : 'text-red-400'}`}>
                        {row.average_rating.toFixed(2)}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-right text-indigo-400">{row.high_performers}</td>
                    <td className="py-2 px-3 text-right text-red-400">{row.low_performers}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-slate-400 text-sm text-center py-8">No project data available</p>
        )}
      </div>

      {/* Talent Exceptions Table */}
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
        <h2 className="text-white font-semibold text-base mb-4">
          Talent Data Quality Exceptions
          <span className="ml-2 bg-red-500/20 text-red-400 border border-red-500/30 text-xs px-2 py-0.5 rounded">
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
