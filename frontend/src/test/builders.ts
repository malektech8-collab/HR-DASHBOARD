/**
 * Test builders.
 *
 * `UploadPreview` has fourteen fields. A test that spells all of them out
 * obscures the one it is about, and the next person copies the whole block.
 * These give a valid default and let a test name only what matters.
 */
import type {
  DomainStatus,
  OnboardingStatus,
  UploadPreview,
  Violation,
} from '../lib/uploads';
import type { CoverageItem, SuppressionItem } from '../lib/types';

export function aViolation(over: Partial<Violation> = {}): Violation {
  return {
    rule: 'date-range',
    row: 47,
    column: 'joining_date',
    message_en: "Row 47, Joining Date: date '0025-01-26' is outside the plausible range.",
    message_ar: "الصف 47، تاريخ الانضمام: التاريخ '0025-01-26' خارج النطاق المعقول.",
    ...over,
  };
}

/** N violations in one column — the commonest real shape, and the one the
 *  by-column view exists for. */
export function violationsInOneColumn(count: number, column = 'joining_date'): Violation[] {
  return Array.from({ length: count }, (_, i) =>
    aViolation({ row: i + 2, column }));
}

export function aPreview(over: Partial<UploadPreview> = {}): UploadPreview {
  return {
    upload: {
      upload_id: 'test-upload',
      table: 'employees',
      original_filename: 'Book1 (final).csv',
      size_bytes: 1024,
      sha256: 'abc123',
      staged_at: '2026-08-12T09:00:00',
      committed_at: null,
    },
    row_count: 20,
    columns_present: ['employee_id', 'employee_name'],
    columns_missing: [],
    columns_unexpected: [],
    rejects: [],
    exceptions: [],
    can_commit: true,
    suggested_coverage_start: null,
    suggested_coverage_end: null,
    coverage_required: false,
    history_required: false,
    ...over,
  };
}

export function aSuppression(over: Partial<SuppressionItem> = {}): SuppressionItem {
  return {
    key: 'absence_days',
    mart: 'mart_attendance_kpis',
    missing_domains: ['attendance'],
    reason: 'not_provided',
    message_en: 'Not yet provided: Attendance.',
    message_ar: 'لم يتم تقديم البيانات بعد: الحضور.',
    ...over,
  };
}

export function aCoverageItem(over: Partial<CoverageItem> = {}): CoverageItem {
  return {
    domain: 'attendance',
    domain_label_en: 'Attendance',
    domain_label_ar: 'الحضور',
    declared_start: '2026-08-01',
    declared_end: '2026-08-07',
    covered_days: 6,
    expected_days: 27,
    coverage_pct: 22.2,
    message_en: 'Covers 6 of 27 working days (2026-08-01 to 2026-08-07).',
    message_ar: 'يغطي 6 من 27 يوم عمل (2026-08-01 إلى 2026-08-07).',
    ...over,
  };
}

export function aDomainStatus(over: Partial<DomainStatus> = {}): DomainStatus {
  return {
    domain: 'employees',
    label_en: 'Employees',
    label_ar: 'الموظفون',
    kind: 'contracted',
    contracted: true,
    declared: true,
    provided: true,
    row_count: 20,
    coverage_start: null,
    coverage_end: null,
    covered_days: null,
    expected_days: null,
    history_since: '2024-01-15',
    available: true,
    unavailable_reason: null,
    ...over,
  };
}

export function anOnboardingStatus(
  domains: DomainStatus[],
  over: Partial<OnboardingStatus> = {},
): OnboardingStatus {
  return {
    data_mode: 'real',
    report_month: '2026-08',
    domains,
    ...over,
  };
}
