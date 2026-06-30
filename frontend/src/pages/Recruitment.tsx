import React, { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { 
  fetchRecruitmentSummary,
  fetchRecruitmentPipeline,
  fetchRecruitmentTrends,
  fetchRecruitmentByProject,
  fetchRecruitmentByDepartment,
  fetchTimeToFill,
  fetchSourceEffectiveness,
  fetchOfferAcceptance,
  fetchOnboardingStatus,
  fetchWorkforcePlanVsActual,
  fetchRecruitmentExceptions
} from '../lib/api';
import type { 
  RecruitmentSummaryData,
  RecruitmentPipelineData,
  RecruitmentTrendsData,
  RecruitmentByProjectData,
  RecruitmentByDepartmentData,
  TimeToFillData,
  SourceEffectivenessData,
  OfferAcceptanceData,
  OnboardingStatusData,
  WorkforcePlanVsActualData,
  DQExceptionItem
} from '../lib/types';
import { KpiCard } from '../components/cards/KpiCard';
import { ExceptionTable } from '../components/tables/ExceptionTable';
import { UserPlus, ShieldAlert, RefreshCw } from 'lucide-react';

export const Recruitment: React.FC = () => {
  const [summary, setSummary] = useState<RecruitmentSummaryData | null>(null);
  const [pipeline, setPipeline] = useState<RecruitmentPipelineData | null>(null);
  const [trends, setTrends] = useState<RecruitmentTrendsData | null>(null);
  const [byProject, setByProject] = useState<RecruitmentByProjectData | null>(null);
  const [byDepartment, setByDepartment] = useState<RecruitmentByDepartmentData | null>(null);
  const [timeToFill, setTimeToFill] = useState<TimeToFillData | null>(null);
  const [sourceEffectiveness, setSourceEffectiveness] = useState<SourceEffectivenessData | null>(null);
  const [offerAcceptance, setOfferAcceptance] = useState<OfferAcceptanceData | null>(null);
  const [onboardingStatus, setOnboardingStatus] = useState<OnboardingStatusData | null>(null);
  const [workforcePlan, setWorkforcePlan] = useState<WorkforcePlanVsActualData | null>(null);
  const [exceptions, setExceptions] = useState<DQExceptionItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [
        sumRes, pipeRes, trendRes, projRes, deptRes, ttfRes, sourceRes, offerRes, onbRes, planRes, excRes
      ] = await Promise.all([
        fetchRecruitmentSummary(),
        fetchRecruitmentPipeline(),
        fetchRecruitmentTrends(),
        fetchRecruitmentByProject(),
        fetchRecruitmentByDepartment(),
        fetchTimeToFill(),
        fetchSourceEffectiveness(),
        fetchOfferAcceptance(),
        fetchOnboardingStatus(),
        fetchWorkforcePlanVsActual(),
        fetchRecruitmentExceptions()
      ]);

      setSummary(sumRes);
      setPipeline(pipeRes);
      setTrends(trendRes);
      setByProject(projRes);
      setByDepartment(deptRes);
      setTimeToFill(ttfRes);
      setSourceEffectiveness(sourceRes);
      setOfferAcceptance(offerRes);
      setOnboardingStatus(onbRes);
      setWorkforcePlan(planRes);
      setExceptions(excRes.exceptions);
    } catch (err: any) {
      console.error("Error loading Recruitment page data:", err);
      setError(err?.message || "Failed to load Recruitment dashboard data.");
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
        <span className="text-sm text-muted-foreground font-semibold">Compiling Recruitment & Hiring metrics...</span>
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

  // Find specific KPIs
  const getKpi = (key: string) => summary.kpis.find(k => k.key === key);

  const openReqsKpi = getKpi('open_requisitions');
  const approvedVacKpi = getKpi('approved_vacancies');
  const pipelineKpi = getKpi('candidates_in_pipeline');
  const interviewsKpi = getKpi('interviews_scheduled');
  const offersKpi = getKpi('offers_extended');
  const offerAcceptanceKpi = getKpi('offer_acceptance_pct');
  const hiresKpi = getKpi('hires_this_month');
  const ttfKpi = getKpi('average_time_to_fill');
  const overdueReqsKpi = getKpi('overdue_requisitions');
  const fulfillmentKpi = getKpi('workforce_plan_fulfillment_pct');
  const exceptionsKpi = getKpi('recruitment_exception_count');

  // Chart options configurations
  const pipelineData = pipeline?.pipeline.map(p => ({
    name: p.pipeline_stage,
    value: p.candidate_count
  })) || [];

  const funnelOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: '{a} <br/>{b} : {c}' },
    toolbox: { feature: { saveAsImage: {} } },
    legend: { data: pipelineData.map(d => d.name), textStyle: { color: 'var(--foreground)' } },
    series: [
      {
        name: 'Hiring Funnel',
        type: 'funnel',
        left: '10%',
        top: 60,
        bottom: 20,
        width: '80%',
        min: 0,
        max: pipelineData.length > 0 ? Math.max(...pipelineData.map(d => d.value)) : 100,
        minSize: '0%',
        maxSize: '100%',
        sort: 'descending',
        gap: 2,
        label: { show: true, position: 'inside' },
        labelLine: { show: false },
        itemStyle: { borderColor: '#fff', borderWidth: 1 },
        data: pipelineData
      }
    ]
  };

  const trendsOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { data: ['Requisitions Opened', 'Hires'], textStyle: { color: 'var(--foreground)' } },
    xAxis: { type: 'category', data: trends?.trends.map(t => t.period) || [], axisLabel: { color: 'var(--foreground)' } },
    yAxis: { type: 'value', axisLabel: { color: 'var(--foreground)' } },
    series: [
      { name: 'Requisitions Opened', type: 'line', smooth: true, data: trends?.trends.map(t => t.requisitions_opened) || [] },
      { name: 'Hires', type: 'line', smooth: true, data: trends?.trends.map(t => t.hires) || [] }
    ]
  };

  const offerAcceptanceOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item' },
    legend: { bottom: '0', left: 'center', textStyle: { color: 'var(--foreground)' } },
    series: [
      {
        name: 'Offer Status',
        type: 'pie',
        radius: ['45%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 8, borderColor: 'var(--card)', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: offerAcceptance?.offers.map(o => ({ name: o.offer_status, value: o.offer_count })) || []
      }
    ]
  };

  const projectReqsOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { textStyle: { color: 'var(--foreground)' } },
    xAxis: { type: 'value', axisLabel: { color: 'var(--foreground)' } },
    yAxis: { type: 'category', data: byProject?.projects.map(p => p.project) || [], axisLabel: { color: 'var(--foreground)' } },
    series: [
      { name: 'Total Requisitions', type: 'bar', data: byProject?.projects.map(p => p.total_requisitions) || [] },
      { name: 'Open Requisitions', type: 'bar', data: byProject?.projects.map(p => p.open_requisitions) || [] }
    ]
  };

  const deptReqsOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { textStyle: { color: 'var(--foreground)' } },
    xAxis: { type: 'category', data: byDepartment?.departments.map(d => d.department) || [], axisLabel: { color: 'var(--foreground)' } },
    yAxis: { type: 'value', axisLabel: { color: 'var(--foreground)' } },
    series: [
      { name: 'Total Requisitions', type: 'bar', data: byDepartment?.departments.map(d => d.total_requisitions) || [] },
      { name: 'Open Requisitions', type: 'bar', data: byDepartment?.departments.map(d => d.open_requisitions) || [] }
    ]
  };

  const ttfOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'category', data: timeToFill?.time_to_fill.map(t => `${t.department}\n(${t.project})`) || [], axisLabel: { color: 'var(--foreground)', interval: 0, rotate: 15 } },
    yAxis: { type: 'value', name: 'Days', axisLabel: { color: 'var(--foreground)' }, nameTextStyle: { color: 'var(--foreground)' } },
    series: [
      { name: 'Avg Days to Fill', type: 'bar', data: timeToFill?.time_to_fill.map(t => t.average_time_to_fill) || [], itemStyle: { color: '#3b82f6' } }
    ]
  };

  const sourceEffectivenessOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: '{a} <br/>{b} : {c} ({d}%)' },
    legend: { bottom: '0', left: 'center', textStyle: { color: 'var(--foreground)' } },
    series: [
      {
        name: 'Candidate Sources',
        type: 'pie',
        radius: '60%',
        center: ['50%', '45%'],
        data: sourceEffectiveness?.sources.map(s => ({ name: s.source, value: s.candidate_count })) || []
      }
    ]
  };

  const onboardingOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item' },
    legend: { bottom: '0', left: 'center', textStyle: { color: 'var(--foreground)' } },
    series: [
      {
        name: 'Onboarding Status',
        type: 'pie',
        radius: '60%',
        center: ['50%', '45%'],
        data: onboardingStatus?.onboarding.map(o => ({ name: o.onboarding_status, value: o.hire_count })) || []
      }
    ]
  };

  const planVsActualOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { textStyle: { color: 'var(--foreground)' } },
    xAxis: { type: 'category', data: workforcePlan?.plan.map(p => `${p.project}\n(${p.department})`) || [], axisLabel: { color: 'var(--foreground)', interval: 0, rotate: 15 } },
    yAxis: { type: 'value', axisLabel: { color: 'var(--foreground)' } },
    series: [
      { name: 'Planned Headcount', type: 'bar', data: workforcePlan?.plan.map(p => p.planned_headcount) || [] },
      { name: 'Actual Headcount', type: 'bar', data: workforcePlan?.plan.map(p => p.actual_headcount) || [] }
    ]
  };

  return (
    <div className="p-6 space-y-6">
      {/* Title block */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
            <UserPlus className="w-8 h-8 text-primary" />
            Recruitment & Workforce Planning Dashboard
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Analyzing hiring pipeline funnel, requisitions status, time-to-fill SLA aging, onboarding tracking, and workforce planning headcount targets.
          </p>
        </div>
        <div className="px-4 py-2 bg-card border border-border rounded-lg text-sm text-muted-foreground flex items-center gap-2">
          <span>Report Month:</span>
          <span className="font-semibold text-foreground">{summary.report_month}</span>
        </div>
      </div>

      {/* Row 1: 5 KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {openReqsKpi && (
          <KpiCard 
            label={openReqsKpi.label}
            value={openReqsKpi.value}
            unit={openReqsKpi.unit}
            status={openReqsKpi.status as any}
          />
        )}
        {approvedVacKpi && (
          <KpiCard 
            label={approvedVacKpi.label}
            value={approvedVacKpi.value}
            unit={approvedVacKpi.unit}
            status={approvedVacKpi.status as any}
          />
        )}
        {pipelineKpi && (
          <KpiCard 
            label={pipelineKpi.label}
            value={pipelineKpi.value}
            unit={pipelineKpi.unit}
            status={pipelineKpi.status as any}
          />
        )}
        {interviewsKpi && (
          <KpiCard 
            label={interviewsKpi.label}
            value={interviewsKpi.value}
            unit={interviewsKpi.unit}
            status={interviewsKpi.status as any}
          />
        )}
        {offersKpi && (
          <KpiCard 
            label={offersKpi.label}
            value={offersKpi.value}
            unit={offersKpi.unit}
            status={offersKpi.status as any}
          />
        )}
      </div>

      {/* Row 2: 6 KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
        {offerAcceptanceKpi && (
          <KpiCard 
            label={offerAcceptanceKpi.label}
            value={offerAcceptanceKpi.value}
            unit={offerAcceptanceKpi.unit}
            status={offerAcceptanceKpi.status as any}
          />
        )}
        {hiresKpi && (
          <KpiCard 
            label={hiresKpi.label}
            value={hiresKpi.value}
            unit={hiresKpi.unit}
            status={hiresKpi.status as any}
          />
        )}
        {ttfKpi && (
          <KpiCard 
            label={ttfKpi.label}
            value={ttfKpi.value}
            unit={ttfKpi.unit}
            status={ttfKpi.status as any}
          />
        )}
        {overdueReqsKpi && (
          <KpiCard 
            label={overdueReqsKpi.label}
            value={overdueReqsKpi.value}
            unit={overdueReqsKpi.unit}
            status={overdueReqsKpi.status as any}
          />
        )}
        {fulfillmentKpi && (
          <KpiCard 
            label={fulfillmentKpi.label}
            value={fulfillmentKpi.value}
            unit={fulfillmentKpi.unit}
            status={fulfillmentKpi.status as any}
          />
        )}
        {exceptionsKpi && (
          <KpiCard 
            label={exceptionsKpi.label}
            value={exceptionsKpi.value}
            unit={exceptionsKpi.unit}
            status={exceptionsKpi.status as any}
          />
        )}
      </div>

      {/* Row 3: Funnel & Requisitions Opened/Hired line */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
          <h3 className="text-lg font-bold text-foreground mb-4">Hiring Pipeline Funnel</h3>
          <ReactECharts option={funnelOption} style={{ height: '350px' }} />
        </div>
        <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
          <h3 className="text-lg font-bold text-foreground mb-4">Requisition & Hiring Trends</h3>
          <ReactECharts option={trendsOption} style={{ height: '350px' }} />
        </div>
      </div>

      {/* Row 4: Hires Trend & Offer Acceptance Donut */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-card border border-border p-6 rounded-xl shadow-sm lg:col-span-2">
          <h3 className="text-lg font-bold text-foreground mb-4">Recruitment Fulfillment vs Plan by Project/Dept</h3>
          <ReactECharts option={planVsActualOption} style={{ height: '350px' }} />
        </div>
        <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
          <h3 className="text-lg font-bold text-foreground mb-4">Offer Status Split</h3>
          <ReactECharts option={offerAcceptanceOption} style={{ height: '350px' }} />
        </div>
      </div>

      {/* Row 5: Requisitions by Project & Department */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
          <h3 className="text-lg font-bold text-foreground mb-4">Requisitions by Project</h3>
          <ReactECharts option={projectReqsOption} style={{ height: '350px' }} />
        </div>
        <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
          <h3 className="text-lg font-bold text-foreground mb-4">Requisitions by Department</h3>
          <ReactECharts option={deptReqsOption} style={{ height: '350px' }} />
        </div>
      </div>

      {/* Row 6: Time-to-Fill & Candidate Source Effectiveness */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
          <h3 className="text-lg font-bold text-foreground mb-4">Average Time-to-Fill (Days)</h3>
          <ReactECharts option={ttfOption} style={{ height: '350px' }} />
        </div>
        <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
          <h3 className="text-lg font-bold text-foreground mb-4">Candidate Sourcing Effectiveness</h3>
          <ReactECharts option={sourceEffectivenessOption} style={{ height: '350px' }} />
        </div>
      </div>

      {/* Row 7: Onboarding Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
          <h3 className="text-lg font-bold text-foreground mb-4">Onboarding Status</h3>
          <ReactECharts option={onboardingOption} style={{ height: '350px' }} />
        </div>
        <div className="bg-card border border-border p-6 rounded-xl shadow-sm lg:col-span-2">
          <div className="h-full flex flex-col justify-between">
            <div>
              <h3 className="text-lg font-bold text-foreground mb-2">Hiring Pipeline Context & Logic</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Requisitions represent approved, active roles that recruiters are actively working on. Time-to-Fill is measured from the requisition's official approval date to the hire's onboarding start date.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6">
                <div className="p-4 bg-muted/40 rounded-lg border border-border/60">
                  <span className="text-xs text-muted-foreground font-semibold uppercase">Default SLA Sourcing Limit</span>
                  <p className="text-lg font-bold text-foreground mt-1">45 Days</p>
                  <p className="text-xs text-muted-foreground mt-1">Applied if target date is not set</p>
                </div>
                <div className="p-4 bg-muted/40 rounded-lg border border-border/60">
                  <span className="text-xs text-muted-foreground font-semibold uppercase">Decided Offers Definition</span>
                  <p className="text-lg font-bold text-foreground mt-1">Accepted / Decided Ratio</p>
                  <p className="text-xs text-muted-foreground mt-1">Excludes pending candidates</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Row 8: Recruitment Exceptions Log */}
      <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <ShieldAlert className="w-5 h-5 text-critical" />
          <h3 className="text-lg font-bold text-foreground">Recruitment & Hiring Exception Log</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          The exceptions below capture missing ownership recruiters, overdue SLA requisitions, duplicate candidate profiles, planning excess headcounts, and invalid candidate references.
        </p>
        <ExceptionTable data={exceptions} />
      </div>
    </div>
  );
};
