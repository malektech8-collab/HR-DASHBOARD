import type { 
  ExecutiveSummaryData, 
  DataQualitySummaryData, 
  DQExceptionsData, 
  RefreshStatus,
  WorkforceSummaryData,
  WorkforceTrendsData,
  WorkforceDistributionData,
  ExpiryAgingData,
  PayrollSummaryData,
  PayrollTrendsData,
  PayrollByProjectData,
  PayrollByDepartmentData,
  PayrollComponentsData,
  PayrollVarianceData,
  PayrollExceptionsData,
  AttendanceSummaryData,
  AttendanceTrendsData,
  AttendanceByProjectData,
  AttendanceByDepartmentData,
  AttendanceLateArrivalData,
  AttendanceOvertimeData,
  AttendanceMissingPunchesData,
  AttendanceExceptionsData,
  ComplianceSummaryData,
  SaudizationSummaryData,
  SaudizationByProjectData,
  SaudizationByDepartmentData,
  DocumentExpiryData,
  GosiStatusData,
  WpsStatusData,
  ComplianceExceptionsData,
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
  RecruitmentExceptionsData,
  CommandCenterOverviewData,
  ModuleHealthResponse,
  PriorityAlertResponse,
  ExceptionSummaryResponse,
  FreshnessResponse,
  FilterOptionsResponse,
  NavigationStatusResponse,
  QaIndexResponse
} from './types';

// Every call goes through lib/http.ts, which attaches the auth token. Before
// that existed this file had 77 fetch sites and none of them sent one, so the
// six routes P0-2 protected were unreachable from the frontend.
import { API_BASE_URL, getJson, postJson } from './http';

export { API_BASE_URL };

export async function fetchRefreshStatus(): Promise<RefreshStatus> {
  return getJson<RefreshStatus>('/api/meta/refresh-status');
}

export async function fetchExecutiveSummary(): Promise<ExecutiveSummaryData> {
  return getJson<ExecutiveSummaryData>('/api/executive/summary');
}

export async function fetchDataQualitySummary(): Promise<DataQualitySummaryData> {
  return getJson<DataQualitySummaryData>('/api/data-quality/summary');
}

export async function fetchDataQualityExceptions(): Promise<DQExceptionsData> {
  return getJson<DQExceptionsData>('/api/data-quality/exceptions');
}

// Workforce API endpoints
export async function fetchWorkforceSummary(): Promise<WorkforceSummaryData> {
  return getJson<WorkforceSummaryData>('/api/workforce/summary');
}

export async function fetchWorkforceTrends(): Promise<WorkforceTrendsData> {
  return getJson<WorkforceTrendsData>('/api/workforce/trends');
}

export async function fetchWorkforceDistribution(): Promise<WorkforceDistributionData> {
  return getJson<WorkforceDistributionData>('/api/workforce/distribution');
}

export async function fetchWorkforceContractExpiry(): Promise<ExpiryAgingData> {
  return getJson<ExpiryAgingData>('/api/workforce/contract-expiry');
}

export async function fetchWorkforceIqamaExpiry(): Promise<ExpiryAgingData> {
  return getJson<ExpiryAgingData>('/api/workforce/iqama-expiry');
}

export async function fetchWorkforceExceptions(): Promise<DQExceptionsData> {
  return getJson<DQExceptionsData>('/api/workforce/exceptions');
}

// Payroll API endpoints
export async function fetchPayrollSummary(): Promise<PayrollSummaryData> {
  return getJson<PayrollSummaryData>('/api/payroll/summary');
}

export async function fetchPayrollTrends(): Promise<PayrollTrendsData> {
  return getJson<PayrollTrendsData>('/api/payroll/trends');
}

export async function fetchPayrollByProject(): Promise<PayrollByProjectData> {
  return getJson<PayrollByProjectData>('/api/payroll/by-project');
}

export async function fetchPayrollByDepartment(): Promise<PayrollByDepartmentData> {
  return getJson<PayrollByDepartmentData>('/api/payroll/by-department');
}

export async function fetchPayrollComponents(): Promise<PayrollComponentsData> {
  return getJson<PayrollComponentsData>('/api/payroll/components');
}

export async function fetchPayrollVariance(): Promise<PayrollVarianceData> {
  return getJson<PayrollVarianceData>('/api/payroll/variance');
}

export async function fetchPayrollExceptions(): Promise<PayrollExceptionsData> {
  return getJson<PayrollExceptionsData>('/api/payroll/exceptions');
}

// Attendance API endpoints
export async function fetchAttendanceSummary(): Promise<AttendanceSummaryData> {
  return getJson<AttendanceSummaryData>('/api/attendance/summary');
}

export async function fetchAttendanceTrends(): Promise<AttendanceTrendsData> {
  return getJson<AttendanceTrendsData>('/api/attendance/trends');
}

export async function fetchAttendanceByProject(): Promise<AttendanceByProjectData> {
  return getJson<AttendanceByProjectData>('/api/attendance/by-project');
}

export async function fetchAttendanceByDepartment(): Promise<AttendanceByDepartmentData> {
  return getJson<AttendanceByDepartmentData>('/api/attendance/by-department');
}

export async function fetchAttendanceLateArrival(): Promise<AttendanceLateArrivalData> {
  return getJson<AttendanceLateArrivalData>('/api/attendance/late-arrival');
}

export async function fetchAttendanceOvertime(): Promise<AttendanceOvertimeData> {
  return getJson<AttendanceOvertimeData>('/api/attendance/overtime');
}

export async function fetchAttendanceMissingPunches(): Promise<AttendanceMissingPunchesData> {
  return getJson<AttendanceMissingPunchesData>('/api/attendance/missing-punches');
}

export async function fetchAttendanceExceptions(): Promise<AttendanceExceptionsData> {
  return getJson<AttendanceExceptionsData>('/api/attendance/exceptions');
}

// Compliance API endpoints
export async function fetchComplianceSummary(): Promise<ComplianceSummaryData> {
  return getJson<ComplianceSummaryData>('/api/compliance/summary');
}

export async function fetchSaudizationSummary(): Promise<SaudizationSummaryData> {
  return getJson<SaudizationSummaryData>('/api/compliance/saudization');
}

export async function fetchSaudizationByProject(): Promise<SaudizationByProjectData> {
  return getJson<SaudizationByProjectData>('/api/compliance/saudization-by-project');
}

export async function fetchSaudizationByDepartment(): Promise<SaudizationByDepartmentData> {
  return getJson<SaudizationByDepartmentData>('/api/compliance/saudization-by-department');
}

export async function fetchDocumentExpiry(): Promise<DocumentExpiryData> {
  return getJson<DocumentExpiryData>('/api/compliance/document-expiry');
}

export async function fetchGosiStatus(): Promise<GosiStatusData> {
  return getJson<GosiStatusData>('/api/compliance/gosi');
}

export async function fetchWpsStatus(): Promise<WpsStatusData> {
  return getJson<WpsStatusData>('/api/compliance/wps');
}

export async function fetchComplianceExceptions(): Promise<ComplianceExceptionsData> {
  return getJson<ComplianceExceptionsData>('/api/compliance/exceptions');
}

// Employee Relations API endpoints
export async function fetchErSummary(): Promise<ErSummaryData> {
  return getJson<ErSummaryData>('/api/er/summary');
}

export async function fetchErTrends(): Promise<ErTrendsData> {
  return getJson<ErTrendsData>('/api/er/trends');
}

export async function fetchErByProject(): Promise<ErCasesByProjectData> {
  return getJson<ErCasesByProjectData>('/api/er/by-project');
}

export async function fetchErByDepartment(): Promise<ErCasesByDepartmentData> {
  return getJson<ErCasesByDepartmentData>('/api/er/by-department');
}

export async function fetchErCaseTypes(): Promise<ErCaseTypeData> {
  return getJson<ErCaseTypeData>('/api/er/case-types');
}

export async function fetchErStatus(): Promise<ErCaseStatusData> {
  return getJson<ErCaseStatusData>('/api/er/status');
}

export async function fetchErSla(): Promise<ErSlaPerformanceData> {
  return getJson<ErSlaPerformanceData>('/api/er/sla');
}

export async function fetchErAging(): Promise<ErAgingBucketData> {
  return getJson<ErAgingBucketData>('/api/er/aging');
}

export async function fetchErExceptions(): Promise<ErExceptionsData> {
  return getJson<ErExceptionsData>('/api/er/exceptions');
}

// Recruitment API endpoints
export async function fetchRecruitmentSummary(): Promise<RecruitmentSummaryData> {
  return getJson<RecruitmentSummaryData>('/api/recruitment/summary');
}

export async function fetchRecruitmentPipeline(): Promise<RecruitmentPipelineData> {
  return getJson<RecruitmentPipelineData>('/api/recruitment/pipeline');
}

export async function fetchRecruitmentTrends(): Promise<RecruitmentTrendsData> {
  return getJson<RecruitmentTrendsData>('/api/recruitment/trends');
}

export async function fetchRecruitmentByProject(): Promise<RecruitmentByProjectData> {
  return getJson<RecruitmentByProjectData>('/api/recruitment/by-project');
}

export async function fetchRecruitmentByDepartment(): Promise<RecruitmentByDepartmentData> {
  return getJson<RecruitmentByDepartmentData>('/api/recruitment/by-department');
}

export async function fetchTimeToFill(): Promise<TimeToFillData> {
  return getJson<TimeToFillData>('/api/recruitment/time-to-fill');
}

export async function fetchSourceEffectiveness(): Promise<SourceEffectivenessData> {
  return getJson<SourceEffectivenessData>('/api/recruitment/source-effectiveness');
}

export async function fetchOfferAcceptance(): Promise<OfferAcceptanceData> {
  return getJson<OfferAcceptanceData>('/api/recruitment/offers');
}

export async function fetchOnboardingStatus(): Promise<OnboardingStatusData> {
  return getJson<OnboardingStatusData>('/api/recruitment/onboarding');
}

export async function fetchWorkforcePlanVsActual(): Promise<WorkforcePlanVsActualData> {
  return getJson<WorkforcePlanVsActualData>('/api/recruitment/workforce-plan');
}

export async function fetchRecruitmentExceptions(): Promise<RecruitmentExceptionsData> {
  return getJson<RecruitmentExceptionsData>('/api/recruitment/exceptions');
}

// Talent, Performance, Learning & Succession API endpoints
export async function fetchTalentSummary(): Promise<TalentSummaryData> {
  return getJson<TalentSummaryData>('/api/talent/summary');
}

export async function fetchPerformanceDistribution(): Promise<PerformanceDistributionData> {
  return getJson<PerformanceDistributionData>('/api/talent/performance-distribution');
}

export async function fetchPerformanceTrends(): Promise<PerformanceTrendsData> {
  return getJson<PerformanceTrendsData>('/api/talent/trends');
}

export async function fetchPerformanceByProject(): Promise<PerformanceByProjectData> {
  return getJson<PerformanceByProjectData>('/api/talent/by-project');
}

export async function fetchPerformanceByDepartment(): Promise<PerformanceByDepartmentData> {
  return getJson<PerformanceByDepartmentData>('/api/talent/by-department');
}

export async function fetchGoalCompletion(): Promise<GoalCompletionData> {
  return getJson<GoalCompletionData>('/api/talent/goals');
}

export async function fetchCompetencyGaps(): Promise<CompetencyGapData> {
  return getJson<CompetencyGapData>('/api/talent/competency-gaps');
}

export async function fetchLearningCompletion(): Promise<LearningCompletionData> {
  return getJson<LearningCompletionData>('/api/talent/learning');
}

export async function fetchLearningByProject(): Promise<LearningByProjectData> {
  return getJson<LearningByProjectData>('/api/talent/learning-by-project');
}

export async function fetchSuccessionCoverage(): Promise<SuccessionCoverageData> {
  return getJson<SuccessionCoverageData>('/api/talent/succession');
}

export async function fetchSuccessorReadiness(): Promise<SuccessorReadinessData> {
  return getJson<SuccessorReadinessData>('/api/talent/succession-readiness');
}

export async function fetchTalentRisk(): Promise<TalentRiskData> {
  return getJson<TalentRiskData>('/api/talent/risk');
}

export async function fetchTalentExceptions(): Promise<TalentExceptionsData> {
  return getJson<TalentExceptionsData>('/api/talent/exceptions');
}

// Command Center API endpoints
export async function fetchCommandCenterOverview(): Promise<CommandCenterOverviewData> {
  return getJson<CommandCenterOverviewData>('/api/command-center/overview');
}

export async function fetchCommandCenterModuleHealth(): Promise<ModuleHealthResponse> {
  return getJson<ModuleHealthResponse>('/api/command-center/module-health');
}

export async function fetchCommandCenterPriorityAlerts(): Promise<PriorityAlertResponse> {
  return getJson<PriorityAlertResponse>('/api/command-center/priority-alerts');
}

export async function fetchCommandCenterExceptions(): Promise<ExceptionSummaryResponse> {
  return getJson<ExceptionSummaryResponse>('/api/command-center/exceptions');
}

export async function fetchCommandCenterDataFreshness(): Promise<FreshnessResponse> {
  return getJson<FreshnessResponse>('/api/command-center/data-freshness');
}

export async function fetchCommandCenterFilterOptions(): Promise<FilterOptionsResponse> {
  return getJson<FilterOptionsResponse>('/api/command-center/filter-options');
}

export async function fetchCommandCenterNavigationStatus(): Promise<NavigationStatusResponse> {
  return getJson<NavigationStatusResponse>('/api/command-center/navigation-status');
}

export async function fetchCommandCenterQaIndex(): Promise<QaIndexResponse> {
  return getJson<QaIndexResponse>('/api/command-center/qa-index');
}

// Data Management API endpoints
export interface TemplateInfo {
  name: string;
  filename: string;
  /** Bilingual, from the contract - the endpoint has returned it since 1b-ii;
   *  the type simply never declared it. */
  label: string;
  description: string;
  available: boolean;
}

export async function fetchTemplates(): Promise<TemplateInfo[]> {
  return getJson<TemplateInfo[]>('/api/data/templates');
}

export function getTemplateDownloadUrl(name: string): string {
  return `${API_BASE_URL}/api/data/templates?name=${encodeURIComponent(name)}`;
}

// uploadFile() WAS HERE and is deleted (TD-005). It POSTed to
// /api/data/upload, which P0-2 replaced with the staged flow: a single call
// that wrote straight to data/silver became stage -> preview -> commit. It was
// already dead - no page called it - and after P0-2 it was dead AND wrong, so
// the first contributor to wire an upload UI from it would have built against
// an endpoint that no longer exists. See lib/uploads.ts.

export interface RefreshReport {
  status: string;
  return_code: number;
  stdout: string;
  stderr: string;
  execution_time_seconds: number;
}

export async function triggerRefresh(): Promise<RefreshReport> {
  return postJson<RefreshReport>('/api/data/refresh');
}
