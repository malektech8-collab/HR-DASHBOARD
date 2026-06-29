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

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `API error: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchRefreshStatus(): Promise<RefreshStatus> {
  const res = await fetch(`${API_BASE_URL}/api/meta/refresh-status`);
  return handleResponse<RefreshStatus>(res);
}

export async function fetchExecutiveSummary(): Promise<ExecutiveSummaryData> {
  const res = await fetch(`${API_BASE_URL}/api/executive/summary`);
  return handleResponse<ExecutiveSummaryData>(res);
}

export async function fetchDataQualitySummary(): Promise<DataQualitySummaryData> {
  const res = await fetch(`${API_BASE_URL}/api/data-quality/summary`);
  return handleResponse<DataQualitySummaryData>(res);
}

export async function fetchDataQualityExceptions(): Promise<DQExceptionsData> {
  const res = await fetch(`${API_BASE_URL}/api/data-quality/exceptions`);
  return handleResponse<DQExceptionsData>(res);
}

// Workforce API endpoints
export async function fetchWorkforceSummary(): Promise<WorkforceSummaryData> {
  const res = await fetch(`${API_BASE_URL}/api/workforce/summary`);
  return handleResponse<WorkforceSummaryData>(res);
}

export async function fetchWorkforceTrends(): Promise<WorkforceTrendsData> {
  const res = await fetch(`${API_BASE_URL}/api/workforce/trends`);
  return handleResponse<WorkforceTrendsData>(res);
}

export async function fetchWorkforceDistribution(): Promise<WorkforceDistributionData> {
  const res = await fetch(`${API_BASE_URL}/api/workforce/distribution`);
  return handleResponse<WorkforceDistributionData>(res);
}

export async function fetchWorkforceContractExpiry(): Promise<ExpiryAgingData> {
  const res = await fetch(`${API_BASE_URL}/api/workforce/contract-expiry`);
  return handleResponse<ExpiryAgingData>(res);
}

export async function fetchWorkforceIqamaExpiry(): Promise<ExpiryAgingData> {
  const res = await fetch(`${API_BASE_URL}/api/workforce/iqama-expiry`);
  return handleResponse<ExpiryAgingData>(res);
}

export async function fetchWorkforceExceptions(): Promise<DQExceptionsData> {
  const res = await fetch(`${API_BASE_URL}/api/workforce/exceptions`);
  return handleResponse<DQExceptionsData>(res);
}

// Payroll API endpoints
export async function fetchPayrollSummary(): Promise<PayrollSummaryData> {
  const res = await fetch(`${API_BASE_URL}/api/payroll/summary`);
  return handleResponse<PayrollSummaryData>(res);
}

export async function fetchPayrollTrends(): Promise<PayrollTrendsData> {
  const res = await fetch(`${API_BASE_URL}/api/payroll/trends`);
  return handleResponse<PayrollTrendsData>(res);
}

export async function fetchPayrollByProject(): Promise<PayrollByProjectData> {
  const res = await fetch(`${API_BASE_URL}/api/payroll/by-project`);
  return handleResponse<PayrollByProjectData>(res);
}

export async function fetchPayrollByDepartment(): Promise<PayrollByDepartmentData> {
  const res = await fetch(`${API_BASE_URL}/api/payroll/by-department`);
  return handleResponse<PayrollByDepartmentData>(res);
}

export async function fetchPayrollComponents(): Promise<PayrollComponentsData> {
  const res = await fetch(`${API_BASE_URL}/api/payroll/components`);
  return handleResponse<PayrollComponentsData>(res);
}

export async function fetchPayrollVariance(): Promise<PayrollVarianceData> {
  const res = await fetch(`${API_BASE_URL}/api/payroll/variance`);
  return handleResponse<PayrollVarianceData>(res);
}

export async function fetchPayrollExceptions(): Promise<PayrollExceptionsData> {
  const res = await fetch(`${API_BASE_URL}/api/payroll/exceptions`);
  return handleResponse<PayrollExceptionsData>(res);
}

// Attendance API endpoints
export async function fetchAttendanceSummary(): Promise<AttendanceSummaryData> {
  const res = await fetch(`${API_BASE_URL}/api/attendance/summary`);
  return handleResponse<AttendanceSummaryData>(res);
}

export async function fetchAttendanceTrends(): Promise<AttendanceTrendsData> {
  const res = await fetch(`${API_BASE_URL}/api/attendance/trends`);
  return handleResponse<AttendanceTrendsData>(res);
}

export async function fetchAttendanceByProject(): Promise<AttendanceByProjectData> {
  const res = await fetch(`${API_BASE_URL}/api/attendance/by-project`);
  return handleResponse<AttendanceByProjectData>(res);
}

export async function fetchAttendanceByDepartment(): Promise<AttendanceByDepartmentData> {
  const res = await fetch(`${API_BASE_URL}/api/attendance/by-department`);
  return handleResponse<AttendanceByDepartmentData>(res);
}

export async function fetchAttendanceLateArrival(): Promise<AttendanceLateArrivalData> {
  const res = await fetch(`${API_BASE_URL}/api/attendance/late-arrival`);
  return handleResponse<AttendanceLateArrivalData>(res);
}

export async function fetchAttendanceOvertime(): Promise<AttendanceOvertimeData> {
  const res = await fetch(`${API_BASE_URL}/api/attendance/overtime`);
  return handleResponse<AttendanceOvertimeData>(res);
}

export async function fetchAttendanceMissingPunches(): Promise<AttendanceMissingPunchesData> {
  const res = await fetch(`${API_BASE_URL}/api/attendance/missing-punches`);
  return handleResponse<AttendanceMissingPunchesData>(res);
}

export async function fetchAttendanceExceptions(): Promise<AttendanceExceptionsData> {
  const res = await fetch(`${API_BASE_URL}/api/attendance/exceptions`);
  return handleResponse<AttendanceExceptionsData>(res);
}

// Compliance API endpoints
export async function fetchComplianceSummary(): Promise<ComplianceSummaryData> {
  const res = await fetch(`${API_BASE_URL}/api/compliance/summary`);
  return handleResponse<ComplianceSummaryData>(res);
}

export async function fetchSaudizationSummary(): Promise<SaudizationSummaryData> {
  const res = await fetch(`${API_BASE_URL}/api/compliance/saudization`);
  return handleResponse<SaudizationSummaryData>(res);
}

export async function fetchSaudizationByProject(): Promise<SaudizationByProjectData> {
  const res = await fetch(`${API_BASE_URL}/api/compliance/saudization-by-project`);
  return handleResponse<SaudizationByProjectData>(res);
}

export async function fetchSaudizationByDepartment(): Promise<SaudizationByDepartmentData> {
  const res = await fetch(`${API_BASE_URL}/api/compliance/saudization-by-department`);
  return handleResponse<SaudizationByDepartmentData>(res);
}

export async function fetchDocumentExpiry(): Promise<DocumentExpiryData> {
  const res = await fetch(`${API_BASE_URL}/api/compliance/document-expiry`);
  return handleResponse<DocumentExpiryData>(res);
}

export async function fetchGosiStatus(): Promise<GosiStatusData> {
  const res = await fetch(`${API_BASE_URL}/api/compliance/gosi`);
  return handleResponse<GosiStatusData>(res);
}

export async function fetchWpsStatus(): Promise<WpsStatusData> {
  const res = await fetch(`${API_BASE_URL}/api/compliance/wps`);
  return handleResponse<WpsStatusData>(res);
}

export async function fetchComplianceExceptions(): Promise<ComplianceExceptionsData> {
  const res = await fetch(`${API_BASE_URL}/api/compliance/exceptions`);
  return handleResponse<ComplianceExceptionsData>(res);
}

// Employee Relations API endpoints
export async function fetchErSummary(): Promise<ErSummaryData> {
  const res = await fetch(`${API_BASE_URL}/api/er/summary`);
  return handleResponse<ErSummaryData>(res);
}

export async function fetchErTrends(): Promise<ErTrendsData> {
  const res = await fetch(`${API_BASE_URL}/api/er/trends`);
  return handleResponse<ErTrendsData>(res);
}

export async function fetchErByProject(): Promise<ErCasesByProjectData> {
  const res = await fetch(`${API_BASE_URL}/api/er/by-project`);
  return handleResponse<ErCasesByProjectData>(res);
}

export async function fetchErByDepartment(): Promise<ErCasesByDepartmentData> {
  const res = await fetch(`${API_BASE_URL}/api/er/by-department`);
  return handleResponse<ErCasesByDepartmentData>(res);
}

export async function fetchErCaseTypes(): Promise<ErCaseTypeData> {
  const res = await fetch(`${API_BASE_URL}/api/er/case-types`);
  return handleResponse<ErCaseTypeData>(res);
}

export async function fetchErStatus(): Promise<ErCaseStatusData> {
  const res = await fetch(`${API_BASE_URL}/api/er/status`);
  return handleResponse<ErCaseStatusData>(res);
}

export async function fetchErSla(): Promise<ErSlaPerformanceData> {
  const res = await fetch(`${API_BASE_URL}/api/er/sla`);
  return handleResponse<ErSlaPerformanceData>(res);
}

export async function fetchErAging(): Promise<ErAgingBucketData> {
  const res = await fetch(`${API_BASE_URL}/api/er/aging`);
  return handleResponse<ErAgingBucketData>(res);
}

export async function fetchErExceptions(): Promise<ErExceptionsData> {
  const res = await fetch(`${API_BASE_URL}/api/er/exceptions`);
  return handleResponse<ErExceptionsData>(res);
}

// Recruitment API endpoints
export async function fetchRecruitmentSummary(): Promise<RecruitmentSummaryData> {
  const res = await fetch(`${API_BASE_URL}/api/recruitment/summary`);
  return handleResponse<RecruitmentSummaryData>(res);
}

export async function fetchRecruitmentPipeline(): Promise<RecruitmentPipelineData> {
  const res = await fetch(`${API_BASE_URL}/api/recruitment/pipeline`);
  return handleResponse<RecruitmentPipelineData>(res);
}

export async function fetchRecruitmentTrends(): Promise<RecruitmentTrendsData> {
  const res = await fetch(`${API_BASE_URL}/api/recruitment/trends`);
  return handleResponse<RecruitmentTrendsData>(res);
}

export async function fetchRecruitmentByProject(): Promise<RecruitmentByProjectData> {
  const res = await fetch(`${API_BASE_URL}/api/recruitment/by-project`);
  return handleResponse<RecruitmentByProjectData>(res);
}

export async function fetchRecruitmentByDepartment(): Promise<RecruitmentByDepartmentData> {
  const res = await fetch(`${API_BASE_URL}/api/recruitment/by-department`);
  return handleResponse<RecruitmentByDepartmentData>(res);
}

export async function fetchTimeToFill(): Promise<TimeToFillData> {
  const res = await fetch(`${API_BASE_URL}/api/recruitment/time-to-fill`);
  return handleResponse<TimeToFillData>(res);
}

export async function fetchSourceEffectiveness(): Promise<SourceEffectivenessData> {
  const res = await fetch(`${API_BASE_URL}/api/recruitment/source-effectiveness`);
  return handleResponse<SourceEffectivenessData>(res);
}

export async function fetchOfferAcceptance(): Promise<OfferAcceptanceData> {
  const res = await fetch(`${API_BASE_URL}/api/recruitment/offers`);
  return handleResponse<OfferAcceptanceData>(res);
}

export async function fetchOnboardingStatus(): Promise<OnboardingStatusData> {
  const res = await fetch(`${API_BASE_URL}/api/recruitment/onboarding`);
  return handleResponse<OnboardingStatusData>(res);
}

export async function fetchWorkforcePlanVsActual(): Promise<WorkforcePlanVsActualData> {
  const res = await fetch(`${API_BASE_URL}/api/recruitment/workforce-plan`);
  return handleResponse<WorkforcePlanVsActualData>(res);
}

export async function fetchRecruitmentExceptions(): Promise<RecruitmentExceptionsData> {
  const res = await fetch(`${API_BASE_URL}/api/recruitment/exceptions`);
  return handleResponse<RecruitmentExceptionsData>(res);
}

// Talent, Performance, Learning & Succession API endpoints
export async function fetchTalentSummary(): Promise<TalentSummaryData> {
  const res = await fetch(`${API_BASE_URL}/api/talent/summary`);
  return handleResponse<TalentSummaryData>(res);
}

export async function fetchPerformanceDistribution(): Promise<PerformanceDistributionData> {
  const res = await fetch(`${API_BASE_URL}/api/talent/performance-distribution`);
  return handleResponse<PerformanceDistributionData>(res);
}

export async function fetchPerformanceTrends(): Promise<PerformanceTrendsData> {
  const res = await fetch(`${API_BASE_URL}/api/talent/trends`);
  return handleResponse<PerformanceTrendsData>(res);
}

export async function fetchPerformanceByProject(): Promise<PerformanceByProjectData> {
  const res = await fetch(`${API_BASE_URL}/api/talent/by-project`);
  return handleResponse<PerformanceByProjectData>(res);
}

export async function fetchPerformanceByDepartment(): Promise<PerformanceByDepartmentData> {
  const res = await fetch(`${API_BASE_URL}/api/talent/by-department`);
  return handleResponse<PerformanceByDepartmentData>(res);
}

export async function fetchGoalCompletion(): Promise<GoalCompletionData> {
  const res = await fetch(`${API_BASE_URL}/api/talent/goals`);
  return handleResponse<GoalCompletionData>(res);
}

export async function fetchCompetencyGaps(): Promise<CompetencyGapData> {
  const res = await fetch(`${API_BASE_URL}/api/talent/competency-gaps`);
  return handleResponse<CompetencyGapData>(res);
}

export async function fetchLearningCompletion(): Promise<LearningCompletionData> {
  const res = await fetch(`${API_BASE_URL}/api/talent/learning`);
  return handleResponse<LearningCompletionData>(res);
}

export async function fetchLearningByProject(): Promise<LearningByProjectData> {
  const res = await fetch(`${API_BASE_URL}/api/talent/learning-by-project`);
  return handleResponse<LearningByProjectData>(res);
}

export async function fetchSuccessionCoverage(): Promise<SuccessionCoverageData> {
  const res = await fetch(`${API_BASE_URL}/api/talent/succession`);
  return handleResponse<SuccessionCoverageData>(res);
}

export async function fetchSuccessorReadiness(): Promise<SuccessorReadinessData> {
  const res = await fetch(`${API_BASE_URL}/api/talent/succession-readiness`);
  return handleResponse<SuccessorReadinessData>(res);
}

export async function fetchTalentRisk(): Promise<TalentRiskData> {
  const res = await fetch(`${API_BASE_URL}/api/talent/risk`);
  return handleResponse<TalentRiskData>(res);
}

export async function fetchTalentExceptions(): Promise<TalentExceptionsData> {
  const res = await fetch(`${API_BASE_URL}/api/talent/exceptions`);
  return handleResponse<TalentExceptionsData>(res);
}

// Command Center API endpoints
export async function fetchCommandCenterOverview(): Promise<CommandCenterOverviewData> {
  const res = await fetch(`${API_BASE_URL}/api/command-center/overview`);
  return handleResponse<CommandCenterOverviewData>(res);
}

export async function fetchCommandCenterModuleHealth(): Promise<ModuleHealthResponse> {
  const res = await fetch(`${API_BASE_URL}/api/command-center/module-health`);
  return handleResponse<ModuleHealthResponse>(res);
}

export async function fetchCommandCenterPriorityAlerts(): Promise<PriorityAlertResponse> {
  const res = await fetch(`${API_BASE_URL}/api/command-center/priority-alerts`);
  return handleResponse<PriorityAlertResponse>(res);
}

export async function fetchCommandCenterExceptions(): Promise<ExceptionSummaryResponse> {
  const res = await fetch(`${API_BASE_URL}/api/command-center/exceptions`);
  return handleResponse<ExceptionSummaryResponse>(res);
}

export async function fetchCommandCenterDataFreshness(): Promise<FreshnessResponse> {
  const res = await fetch(`${API_BASE_URL}/api/command-center/data-freshness`);
  return handleResponse<FreshnessResponse>(res);
}

export async function fetchCommandCenterFilterOptions(): Promise<FilterOptionsResponse> {
  const res = await fetch(`${API_BASE_URL}/api/command-center/filter-options`);
  return handleResponse<FilterOptionsResponse>(res);
}

export async function fetchCommandCenterNavigationStatus(): Promise<NavigationStatusResponse> {
  const res = await fetch(`${API_BASE_URL}/api/command-center/navigation-status`);
  return handleResponse<NavigationStatusResponse>(res);
}

export async function fetchCommandCenterQaIndex(): Promise<QaIndexResponse> {
  const res = await fetch(`${API_BASE_URL}/api/command-center/qa-index`);
  return handleResponse<QaIndexResponse>(res);
}
