export interface KPIItem {
  key: string;
  label: string;
  value: number;
  unit: string;
  trend_value?: number;
  trend_direction?: 'up' | 'down' | 'flat';
  status: 'healthy' | 'warning' | 'critical' | 'neutral';
}

export interface ExecutiveSummaryData {
  report_month: string;
  last_refresh_at: string;
  kpis: KPIItem[];
  charts: {
    months: string[];
    headcount_trend: number[];
    payroll_trend: number[];
  };
}

export interface DataQualitySummaryData {
  data_quality_score: number;
  missing_manager_count: number;
  missing_project_count: number;
  missing_cost_center_count: number;
  missing_nationality_count: number;
  duplicate_employee_count: number;
  invalid_payroll_count: number;
}

export interface DQExceptionItem {
  employee_id: string;
  employee_name: string;
  issue_type: string;
  description: string;
  severity: string;
  recommended_action: string;
}

export interface DQExceptionsData {
  exceptions: DQExceptionItem[];
}

export interface RefreshStatus {
  last_refresh_at: string;
  status: string;
}

export interface WorkforceSummaryData {
  report_month: string;
  kpis: KPIItem[];
}

export interface WorkforceTrendsData {
  months: string[];
  headcount_trend: number[];
}

export interface CategoryDistribution {
  labels: string[];
  values: number[];
}

export interface WorkforceDistributionData {
  department: CategoryDistribution;
  project: CategoryDistribution;
  nationality_group: CategoryDistribution;
  employment_type: CategoryDistribution;
  status: CategoryDistribution;
}

export interface ExpiryAgingData {
  expired: number;
  "0_30": number;
  "31_60": number;
  "61_90": number;
  "90_plus": number;
  missing_date: number;
}

export interface PayrollReconciliationData {
  total_gross_payroll: number;
  sum_displayed_components: number;
  unreconciled_component_difference: number;
  net_payroll: number;
  gross_minus_deductions: number;
  net_unreconciled_difference: number;
  project_payroll_total: number;
  department_payroll_total: number;
  employees_paid_count: number;
  payroll_exception_count: number;
}

export interface PayrollSummaryData {
  report_month: string;
  kpis: KPIItem[];
  reconciliation: PayrollReconciliationData;
}

export interface PayrollTrendItem {
  month: string;
  total_payroll_cost: number;
  basic_salary: number;
  allowances: number;
  overtime: number;
  deductions: number;
  net_payroll: number;
  headcount: number;
}

export interface PayrollTrendsData {
  trends: PayrollTrendItem[];
}

export interface PayrollByProjectItem {
  project: string;
  headcount: number;
  total_payroll_cost: number;
  overtime_cost: number;
}

export interface PayrollByProjectData {
  projects: PayrollByProjectItem[];
}

export interface PayrollByDepartmentItem {
  department: string;
  headcount: number;
  total_payroll_cost: number;
  overtime_cost: number;
}

export interface PayrollByDepartmentData {
  departments: PayrollByDepartmentItem[];
}

export interface PayrollComponentItem {
  component: string;
  amount: number;
}

export interface PayrollComponentsData {
  components: PayrollComponentItem[];
}

export interface PayrollComponentVarianceItem {
  component: string;
  prev_amount: number;
  curr_amount: number;
  change_amount: number;
  change_pct: number;
}

export interface PayrollEmployeeVarianceItem {
  employee_id: string;
  employee_name?: string;
  prev_amount: number;
  curr_amount: number;
  change_amount: number;
  change_pct: number;
}

export interface PayrollVarianceData {
  components: PayrollComponentVarianceItem[];
  employees: PayrollEmployeeVarianceItem[];
}

export interface PayrollExceptionsData {
  exceptions: DQExceptionItem[];
}

export interface AttendanceSummaryData {
  report_month: string;
  kpis: KPIItem[];
}

export interface AttendanceTrendItem {
  month: string;
  attendance_compliance_pct: number;
  absence_days: number;
  late_minutes: number;
  net_late_minutes: number;
  missing_punch_count: number;
  overtime_hours: number;
}

export interface AttendanceTrendsData {
  trends: AttendanceTrendItem[];
}

export interface AttendanceByProjectItem {
  project: string;
  headcount: number;
  attendance_compliance_pct: number;
  absence_days: number;
  late_minutes: number;
  missing_punches: number;
  overtime_hours: number;
  overtime_cost: number;
}

export interface AttendanceByProjectData {
  projects: AttendanceByProjectItem[];
}

export interface AttendanceByDepartmentItem {
  department: string;
  headcount: number;
  attendance_compliance_pct: number;
  absence_days: number;
  late_minutes: number;
  net_late_minutes: number;
  missing_punches: number;
  overtime_hours: number;
  overtime_cost: number;
}

export interface AttendanceByDepartmentData {
  departments: AttendanceByDepartmentItem[];
}

export interface AttendanceLateArrivalItem {
  employee_id: string;
  employee_name: string;
  department?: string;
  project?: string;
  total_late_minutes: number;
  total_excused_minutes: number;
  total_net_late_minutes: number;
  late_arrival_incidents_count: number;
}

export interface AttendanceLateArrivalData {
  late_arrivals: AttendanceLateArrivalItem[];
}

export interface AttendanceOvertimeItem {
  employee_id: string;
  employee_name?: string;
  department?: string;
  project?: string;
  attendance_ot_hours: number;
  payroll_ot_cost: number;
  reconciliation_status: string;
}

export interface AttendanceOvertimeData {
  overtime_records: AttendanceOvertimeItem[];
}

export interface AttendanceMissingPunchesItem {
  employee_id: string;
  employee_name: string;
  department?: string;
  project?: string;
  missing_check_in_count: number;
  missing_check_out_count: number;
  total_missing_punches: number;
}

export interface AttendanceMissingPunchesData {
  missing_punches: AttendanceMissingPunchesItem[];
}

export interface AttendanceExceptionsData {
  exceptions: DQExceptionItem[];
}

export interface ComplianceSummaryData {
  report_month: string;
  kpis: KPIItem[];
}

export interface SaudizationTrendItem {
  period: string;
  saudi_headcount: number;
  non_saudi_headcount: number;
  employees_missing_nationality: number;
  saudization_pct: number;
}

export interface SaudizationSummaryData {
  trends: SaudizationTrendItem[];
}

export interface SaudizationByProjectItem {
  project: string;
  saudi_headcount: number;
  non_saudi_headcount: number;
  employees_missing_nationality: number;
  total_headcount: number;
  saudization_pct: number;
}

export interface SaudizationByProjectData {
  projects: SaudizationByProjectItem[];
}

export interface SaudizationByDepartmentItem {
  department: string;
  saudi_headcount: number;
  non_saudi_headcount: number;
  employees_missing_nationality: number;
  total_headcount: number;
  saudization_pct: number;
}

export interface SaudizationByDepartmentData {
  departments: SaudizationByDepartmentItem[];
}

export interface DocumentExpiryItem {
  expiry_bucket: string;
  iqama_count: number;
  work_permit_count: number;
}

export interface DocumentExpiryData {
  buckets: DocumentExpiryItem[];
}

export interface GosiStatusItem {
  gosi_status: string;
  employee_count: number;
}

export interface GosiStatusData {
  statuses: GosiStatusItem[];
}

export interface WpsStatusItem {
  wps_status: string;
  headcount: number;
}

export interface WpsStatusData {
  statuses: WpsStatusItem[];
}

export interface ComplianceExceptionsData {
  exceptions: DQExceptionItem[];
}

export interface ErSummaryData {
  report_month: string;
  kpis: KPIItem[];
}

export interface ErTrendItem {
  period: string;
  new_cases: number;
  closed_cases: number;
}

export interface ErTrendsData {
  trends: ErTrendItem[];
}

export interface ErCasesByProjectItem {
  project: string;
  total_cases: number;
  open_cases: number;
  closed_cases: number;
  escalated_cases: number;
  compliant_cases: number;
  compliance_pct: number;
}

export interface ErCasesByProjectData {
  projects: ErCasesByProjectItem[];
}

export interface ErCasesByDepartmentItem {
  department: string;
  total_cases: number;
  open_cases: number;
  closed_cases: number;
  escalated_cases: number;
  compliant_cases: number;
  compliance_pct: number;
}

export interface ErCasesByDepartmentData {
  departments: ErCasesByDepartmentItem[];
}

export interface ErCaseTypeItem {
  case_type: string;
  case_count: number;
}

export interface ErCaseTypeData {
  case_types: ErCaseTypeItem[];
}

export interface ErCaseStatusItem {
  case_status: string;
  case_count: number;
}

export interface ErCaseStatusData {
  statuses: ErCaseStatusItem[];
}

export interface ErSlaPerformanceItem {
  category_type: string;
  category: string;
  eligible_count: number;
  compliant_count: number;
  breached_count: number;
  compliance_pct: number;
}

export interface ErSlaPerformanceData {
  performance: ErSlaPerformanceItem[];
}

export interface ErAgingBucketItem {
  aging_bucket: string;
  case_count: number;
}

export interface ErAgingBucketData {
  buckets: ErAgingBucketItem[];
}

export interface ErExceptionsData {
  exceptions: DQExceptionItem[];
}

export interface PipelineStageItem {
  pipeline_stage: string;
  candidate_count: number;
}

export interface RecruitmentPipelineData {
  pipeline: PipelineStageItem[];
}

export interface RecruitmentTrendItem {
  period: string;
  requisitions_opened: number;
  hires: number;
}

export interface RecruitmentTrendsData {
  trends: RecruitmentTrendItem[];
}

export interface RecruitmentByProjectItem {
  project: string;
  total_requisitions: number;
  open_requisitions: number;
  closed_requisitions: number;
  overdue_requisitions: number;
}

export interface RecruitmentByProjectData {
  projects: RecruitmentByProjectItem[];
}

export interface RecruitmentByDepartmentItem {
  department: string;
  total_requisitions: number;
  open_requisitions: number;
  closed_requisitions: number;
  overdue_requisitions: number;
}

export interface RecruitmentByDepartmentData {
  departments: RecruitmentByDepartmentItem[];
}

export interface TimeToFillItem {
  department: string;
  project: string;
  average_time_to_fill: number;
  hire_count: number;
}

export interface TimeToFillData {
  time_to_fill: TimeToFillItem[];
}

export interface SourceEffectivenessItem {
  source: string;
  candidate_count: number;
  hire_count: number;
  conversion_pct: number;
}

export interface SourceEffectivenessData {
  sources: SourceEffectivenessItem[];
}

export interface OfferAcceptanceItem {
  offer_status: string;
  offer_count: number;
}

export interface OfferAcceptanceData {
  offers: OfferAcceptanceItem[];
}

export interface OnboardingStatusItem {
  onboarding_status: string;
  hire_count: number;
}

export interface OnboardingStatusData {
  onboarding: OnboardingStatusItem[];
}

export interface WorkforcePlanVsActualItem {
  project: string;
  department: string;
  planned_headcount: number;
  actual_headcount: number;
  fulfillment_pct: number;
}

export interface WorkforcePlanVsActualData {
  plan: WorkforcePlanVsActualItem[];
}

export interface RecruitmentExceptionsData {
  exceptions: DQExceptionItem[];
}

export interface RecruitmentSummaryData {
  report_month: string;
  kpis: KPIItem[];
}

// Talent, Performance, Learning & Succession types
export interface TalentSummaryData {
  report_month: string;
  kpis: KPIItem[];
}

export interface PerformanceDistributionItem {
  performance_category: string;
  employee_count: number;
}

export interface PerformanceDistributionData {
  distribution: PerformanceDistributionItem[];
}

export interface PerformanceTrendItem {
  period: string;
  total_reviewed: number;
  completed_reviews: number;
  completion_pct: number;
  avg_rating: number;
}

export interface PerformanceTrendsData {
  trends: PerformanceTrendItem[];
}

export interface PerformanceByProjectItem {
  project: string;
  reviewed_count: number;
  average_rating: number;
  high_performers: number;
  low_performers: number;
}

export interface PerformanceByProjectData {
  projects: PerformanceByProjectItem[];
}

export interface PerformanceByDepartmentItem {
  department: string;
  reviewed_count: number;
  average_rating: number;
  high_performers: number;
  low_performers: number;
}

export interface PerformanceByDepartmentData {
  departments: PerformanceByDepartmentItem[];
}

export interface GoalCompletionItem {
  department: string;
  completed_goals: number;
  in_progress_goals: number;
  overdue_goals: number;
  not_started_goals: number;
  cancelled_goals: number;
  eligible_goals: number;
}

export interface GoalCompletionData {
  goals: GoalCompletionItem[];
}

export interface CompetencyGapItem {
  competency_name: string;
  avg_required: number;
  avg_actual: number;
  avg_gap: number;
}

export interface CompetencyGapData {
  gaps: CompetencyGapItem[];
}

export interface LearningCompletionItem {
  category: string;
  completed_enrollments: number;
  eligible_enrollments: number;
  total_hours: number;
}

export interface LearningCompletionData {
  completion: LearningCompletionItem[];
}

export interface LearningByProjectItem {
  project: string;
  department: string;
  completed_enrollments: number;
  total_hours: number;
}

export interface LearningByProjectData {
  projects: LearningByProjectItem[];
}

export interface SuccessionCoverageItem {
  critical_role_id: string;
  role_title: string;
  valid_successor_count: number;
  coverage_status: string;
}

export interface SuccessionCoverageData {
  coverage: SuccessionCoverageItem[];
}

export interface SuccessorReadinessItem {
  readiness: string;
  successor_count: number;
}

export interface SuccessorReadinessData {
  readiness: SuccessorReadinessItem[];
}

export interface TalentRiskItem {
  employee_id: string;
  department: string;
  project: string;
  performance_category: string | null;
  potential_rating: string;
  flight_risk: string;
  risk_category: string;
}

export interface TalentRiskData {
  risks: TalentRiskItem[];
}

export interface TalentExceptionsData {
  exceptions: DQExceptionItem[];
}

export interface CommandCenterOverviewData {
  active_headcount: number;
  payroll_cost: number;
  attendance_compliance_pct: number;
  saudization_pct: number;
  open_er_cases: number;
  open_requisitions: number;
  review_completion_pct: number;
  total_active_exceptions: number;
  modules_healthy: number;
  last_data_refresh: string;
  latest_source_business_date: string | null;
  data_quality_score: number;
}

export interface ModuleHealthItem {
  module_key: string;
  module_label: string;
  route_path: string;
  owner_domain: string;
  api_health_status: string;
  reconciliation_status: string;
  required_marts_present: boolean;
  stale_flag: boolean;
  critical_exception_count: number;
  warning_exception_count: number;
  status: 'Healthy' | 'Warning' | 'Critical' | 'Unknown';
  primary_kpi_count: number;
  screenshot_path?: string;
  qa_report_path?: string;
}

export interface ModuleHealthResponse {
  modules: ModuleHealthItem[];
}

export interface PriorityAlertItem {
  alert_id: string;
  module_key: string;
  module_label: string;
  severity: 'Critical' | 'Warning' | 'Info' | 'Unknown';
  issue_type: string;
  issue_count: number;
  recommended_action: string | null;
  source_mart: string;
  route_path: string;
}

export interface PriorityAlertResponse {
  alerts: PriorityAlertItem[];
}

export interface ExceptionSummaryItem {
  module_key: string;
  module_label: string;
  severity: 'Critical' | 'Warning' | 'Info' | 'Unknown';
  issue_type: string;
  exception_count: number;
  recommended_action: string | null;
  route_path: string;
}

export interface ExceptionSummaryResponse {
  exceptions: ExceptionSummaryItem[];
}

export interface FreshnessItem {
  module_key: string;
  module_label: string;
  source_table: string;
  max_source_date: string | null;
  last_refresh_timestamp: string;
  stale_flag: boolean;
  stale_reason: string;
}

export interface FreshnessResponse {
  freshness: FreshnessItem[];
}

export interface NavigationStatusItem {
  module_key: string;
  page_key: string;
  route_path: string;
  status: string;
}

export interface NavigationStatusResponse {
  navigation: NavigationStatusItem[];
}

export interface FilterOptionsResponse {
  report_month: string;
  companies: string[];
  projects: string[];
  departments: string[];
  cost_centers: string[];
  locations: string[];
  nationalities: string[];
  modules: string[];
}

export interface QaIndexItem {
  module_key: string;
  module_label: string;
  screenshot_path: string;
  screenshot_exists: boolean;
  qa_report_path: string;
  qa_report_exists: boolean;
  raw_api_path: string;
  raw_api_exists: boolean;
  status: 'Complete' | 'Pending';
}

export interface QaIndexResponse {
  qa_index: QaIndexItem[];
}

