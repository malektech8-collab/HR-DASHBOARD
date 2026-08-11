/**
 * Suppression (Phase 2 P0-3, step 2b).
 *
 * A suppressible field is `T | null` - never `undefined`, never an empty array.
 * `null` means "the client has not provided the source domain"; the matching
 * entry in `suppressed` names which domain and why. An empty array would
 * render as an empty chart, and an empty chart claims the period had no
 * events, which is the fabrication this step removes.
 *
 * These are nullable on purpose: the compiler is what forces every call site
 * to decide what to draw instead of a number.
 */
export interface SuppressionItem {
  key: string;
  mart: string;
  missing_domains: string[];
  reason: 'not_provided' | 'not_mapped';
  message_en: string;
  message_ar: string;
}

export interface KPIItem {
  key: string;
  label: string;
  /**
   * Category F: null when the metric is genuinely UNMEASURABLE — the domain
   * was provided, but not for the days it would need. Distinct from a
   * suppressed card, which is absent from `kpis` and named in `suppressed`.
   */
  value: number | null;
  unit: string;
  trend_value?: number;
  trend_direction?: 'up' | 'down' | 'flat';
  status: 'healthy' | 'warning' | 'critical' | 'neutral';
}

export interface ExecutiveSummaryData {
  report_month: string;
  last_refresh_at: string;
  kpis: KPIItem[] | null;
  charts: {
    months: string[];
    headcount_trend: (number | null)[];
    payroll_trend: (number | null)[];
  };
  suppressed?: SuppressionItem[];
}

export interface DataQualitySummaryData {
  data_quality_score: number;
  missing_manager_count: number;
  missing_project_count: number;
  missing_cost_center_count: number;
  missing_nationality_count: number;
  duplicate_employee_count: number;
  invalid_payroll_count: number;
  suppressed?: SuppressionItem[];
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
  exceptions: DQExceptionItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface RefreshStatus {
  last_refresh_at: string;
  status: string;
}

export interface WorkforceSummaryData {
  report_month: string;
  kpis: KPIItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface WorkforceTrendsData {
  months: string[] | null;
  /** Ruling 2: a point before the declared history depth is null, not derived. */
  headcount_trend: (number | null)[] | null;
  suppressed?: SuppressionItem[];
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
  suppressed?: SuppressionItem[];
}

export interface ExpiryAgingData {
  expired: number;
  "0_30": number;
  "31_60": number;
  "61_90": number;
  "90_plus": number;
  missing_date: number;
  suppressed?: SuppressionItem[];
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
  suppressed?: SuppressionItem[];
}

export interface PayrollSummaryData {
  report_month: string;
  kpis: KPIItem[] | null;
  reconciliation: PayrollReconciliationData;
  suppressed?: SuppressionItem[];
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
  trends: PayrollTrendItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface PayrollByProjectItem {
  project: string;
  headcount: number;
  total_payroll_cost: number;
  overtime_cost: number;
}

export interface PayrollByProjectData {
  projects: PayrollByProjectItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface PayrollByDepartmentItem {
  department: string;
  headcount: number;
  total_payroll_cost: number;
  overtime_cost: number;
}

export interface PayrollByDepartmentData {
  departments: PayrollByDepartmentItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface PayrollComponentItem {
  component: string;
  amount: number;
}

export interface PayrollComponentsData {
  components: PayrollComponentItem[] | null;
  suppressed?: SuppressionItem[];
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
  components: PayrollComponentVarianceItem[] | null;
  employees: PayrollEmployeeVarianceItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface PayrollExceptionsData {
  exceptions: DQExceptionItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface AttendanceSummaryData {
  report_month: string;
  kpis: KPIItem[] | null;
  suppressed?: SuppressionItem[];
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
  trends: AttendanceTrendItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface AttendanceByProjectItem {
  project: string;
  headcount: number;
  attendance_compliance_pct: number | null;
  absence_days: number | null;
  late_minutes: number;
  missing_punches: number;
  overtime_hours: number;
  overtime_cost: number;
}

export interface AttendanceByProjectData {
  projects: AttendanceByProjectItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface AttendanceByDepartmentItem {
  department: string;
  headcount: number;
  attendance_compliance_pct: number | null;
  absence_days: number | null;
  late_minutes: number;
  net_late_minutes: number;
  missing_punches: number;
  overtime_hours: number;
  overtime_cost: number;
}

export interface AttendanceByDepartmentData {
  departments: AttendanceByDepartmentItem[] | null;
  suppressed?: SuppressionItem[];
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
  late_arrivals: AttendanceLateArrivalItem[] | null;
  suppressed?: SuppressionItem[];
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
  overtime_records: AttendanceOvertimeItem[] | null;
  suppressed?: SuppressionItem[];
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
  missing_punches: AttendanceMissingPunchesItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface AttendanceExceptionsData {
  exceptions: DQExceptionItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface ComplianceSummaryData {
  report_month: string;
  kpis: KPIItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface SaudizationTrendItem {
  period: string;
  saudi_headcount: number;
  non_saudi_headcount: number;
  employees_missing_nationality: number;
  saudization_pct: number;
}

export interface SaudizationSummaryData {
  trends: SaudizationTrendItem[] | null;
  suppressed?: SuppressionItem[];
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
  projects: SaudizationByProjectItem[] | null;
  suppressed?: SuppressionItem[];
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
  departments: SaudizationByDepartmentItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface DocumentExpiryItem {
  expiry_bucket: string;
  iqama_count: number;
  work_permit_count: number;
}

export interface DocumentExpiryData {
  buckets: DocumentExpiryItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface GosiStatusItem {
  gosi_status: string;
  employee_count: number;
}

export interface GosiStatusData {
  statuses: GosiStatusItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface WpsStatusItem {
  wps_status: string;
  headcount: number;
}

export interface WpsStatusData {
  statuses: WpsStatusItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface ComplianceExceptionsData {
  exceptions: DQExceptionItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface ErSummaryData {
  report_month: string;
  kpis: KPIItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface ErTrendItem {
  period: string;
  new_cases: number;
  closed_cases: number;
}

export interface ErTrendsData {
  trends: ErTrendItem[] | null;
  suppressed?: SuppressionItem[];
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
  projects: ErCasesByProjectItem[] | null;
  suppressed?: SuppressionItem[];
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
  departments: ErCasesByDepartmentItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface ErCaseTypeItem {
  case_type: string;
  case_count: number;
}

export interface ErCaseTypeData {
  case_types: ErCaseTypeItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface ErCaseStatusItem {
  case_status: string;
  case_count: number;
}

export interface ErCaseStatusData {
  statuses: ErCaseStatusItem[] | null;
  suppressed?: SuppressionItem[];
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
  performance: ErSlaPerformanceItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface ErAgingBucketItem {
  aging_bucket: string;
  case_count: number;
}

export interface ErAgingBucketData {
  buckets: ErAgingBucketItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface ErExceptionsData {
  exceptions: DQExceptionItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface PipelineStageItem {
  pipeline_stage: string;
  candidate_count: number;
}

export interface RecruitmentPipelineData {
  pipeline: PipelineStageItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface RecruitmentTrendItem {
  period: string;
  requisitions_opened: number;
  hires: number;
}

export interface RecruitmentTrendsData {
  trends: RecruitmentTrendItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface RecruitmentByProjectItem {
  project: string;
  total_requisitions: number;
  open_requisitions: number;
  closed_requisitions: number;
  overdue_requisitions: number;
}

export interface RecruitmentByProjectData {
  projects: RecruitmentByProjectItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface RecruitmentByDepartmentItem {
  department: string;
  total_requisitions: number;
  open_requisitions: number;
  closed_requisitions: number;
  overdue_requisitions: number;
}

export interface RecruitmentByDepartmentData {
  departments: RecruitmentByDepartmentItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface TimeToFillItem {
  department: string;
  project: string;
  average_time_to_fill: number;
  hire_count: number;
}

export interface TimeToFillData {
  time_to_fill: TimeToFillItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface SourceEffectivenessItem {
  source: string;
  candidate_count: number;
  hire_count: number;
  conversion_pct: number;
}

export interface SourceEffectivenessData {
  sources: SourceEffectivenessItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface OfferAcceptanceItem {
  offer_status: string;
  offer_count: number;
}

export interface OfferAcceptanceData {
  offers: OfferAcceptanceItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface OnboardingStatusItem {
  onboarding_status: string;
  hire_count: number;
}

export interface OnboardingStatusData {
  onboarding: OnboardingStatusItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface WorkforcePlanVsActualItem {
  project: string;
  department: string;
  planned_headcount: number;
  actual_headcount: number;
  fulfillment_pct: number;
}

export interface WorkforcePlanVsActualData {
  plan: WorkforcePlanVsActualItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface RecruitmentExceptionsData {
  exceptions: DQExceptionItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface RecruitmentSummaryData {
  report_month: string;
  kpis: KPIItem[] | null;
  suppressed?: SuppressionItem[];
}

// Talent, Performance, Learning & Succession types
export interface TalentSummaryData {
  report_month: string;
  kpis: KPIItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface PerformanceDistributionItem {
  performance_category: string;
  employee_count: number;
}

export interface PerformanceDistributionData {
  distribution: PerformanceDistributionItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface PerformanceTrendItem {
  period: string;
  total_reviewed: number;
  completed_reviews: number;
  completion_pct: number;
  avg_rating: number;
}

export interface PerformanceTrendsData {
  trends: PerformanceTrendItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface PerformanceByProjectItem {
  project: string;
  reviewed_count: number;
  average_rating: number;
  high_performers: number;
  low_performers: number;
}

export interface PerformanceByProjectData {
  projects: PerformanceByProjectItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface PerformanceByDepartmentItem {
  department: string;
  reviewed_count: number;
  average_rating: number;
  high_performers: number;
  low_performers: number;
}

export interface PerformanceByDepartmentData {
  departments: PerformanceByDepartmentItem[] | null;
  suppressed?: SuppressionItem[];
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
  goals: GoalCompletionItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface CompetencyGapItem {
  competency_name: string;
  avg_required: number;
  avg_actual: number;
  avg_gap: number;
}

export interface CompetencyGapData {
  gaps: CompetencyGapItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface LearningCompletionItem {
  category: string;
  completed_enrollments: number;
  eligible_enrollments: number;
  total_hours: number;
}

export interface LearningCompletionData {
  completion: LearningCompletionItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface LearningByProjectItem {
  project: string;
  department: string;
  completed_enrollments: number;
  total_hours: number;
}

export interface LearningByProjectData {
  projects: LearningByProjectItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface SuccessionCoverageItem {
  critical_role_id: string;
  role_title: string;
  valid_successor_count: number;
  coverage_status: string;
}

export interface SuccessionCoverageData {
  coverage: SuccessionCoverageItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface SuccessorReadinessItem {
  readiness: string;
  successor_count: number;
}

export interface SuccessorReadinessData {
  readiness: SuccessorReadinessItem[] | null;
  suppressed?: SuppressionItem[];
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
  risks: TalentRiskItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface TalentExceptionsData {
  exceptions: DQExceptionItem[] | null;
  suppressed?: SuppressionItem[];
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
  suppressed?: SuppressionItem[];
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
  modules: ModuleHealthItem[] | null;
  suppressed?: SuppressionItem[];
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
  alerts: PriorityAlertItem[] | null;
  suppressed?: SuppressionItem[];
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
  exceptions: ExceptionSummaryItem[] | null;
  suppressed?: SuppressionItem[];
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
  freshness: FreshnessItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface NavigationStatusItem {
  module_key: string;
  page_key: string;
  route_path: string;
  status: string;
}

export interface NavigationStatusResponse {
  navigation: NavigationStatusItem[] | null;
  suppressed?: SuppressionItem[];
}

export interface FilterOptionsResponse {
  report_month: string;
  companies: string[] | null;
  projects: string[] | null;
  departments: string[] | null;
  cost_centers: string[] | null;
  locations: string[] | null;
  nationalities: string[] | null;
  modules: string[] | null;
  suppressed?: SuppressionItem[];
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
  qa_index: QaIndexItem[] | null;
  suppressed?: SuppressionItem[];
}

declare global {
  type ErSummaryData = import('./types').ErSummaryData;
  type ErTrendsData = import('./types').ErTrendsData;
  type ErCasesByProjectData = import('./types').ErCasesByProjectData;
  type ErCasesByDepartmentData = import('./types').ErCasesByDepartmentData;
  type ErCaseTypeData = import('./types').ErCaseTypeData;
  type ErCaseStatusData = import('./types').ErCaseStatusData;
  type ErSlaPerformanceData = import('./types').ErSlaPerformanceData;
  type ErAgingBucketData = import('./types').ErAgingBucketData;
  type ErExceptionsData = import('./types').ErExceptionsData;
  type TalentSummaryData = import('./types').TalentSummaryData;
  type PerformanceDistributionData = import('./types').PerformanceDistributionData;
  type PerformanceTrendsData = import('./types').PerformanceTrendsData;
  type PerformanceByProjectData = import('./types').PerformanceByProjectData;
  type PerformanceByDepartmentData = import('./types').PerformanceByDepartmentData;
  type GoalCompletionData = import('./types').GoalCompletionData;
  type CompetencyGapData = import('./types').CompetencyGapData;
  type LearningCompletionData = import('./types').LearningCompletionData;
  type LearningByProjectData = import('./types').LearningByProjectData;
  type SuccessionCoverageData = import('./types').SuccessionCoverageData;
  type SuccessorReadinessData = import('./types').SuccessorReadinessData;
  type TalentRiskData = import('./types').TalentRiskData;
  type TalentExceptionsData = import('./types').TalentExceptionsData;
}
