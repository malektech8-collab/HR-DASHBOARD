/**
 * The staged upload client (replaces `uploadFile`, closes TD-005).
 *
 * One call became three, and the middle one is the point: a file is staged,
 * validated against its contract, and only committed once a human has seen the
 * result and made the declaration Category F requires.
 *
 * Types mirror the Pydantic models in backend/app/api/data.py exactly.
 */
import { del, getJson, postForm, postJson } from './http';

export interface StagedUpload {
  upload_id: string;
  table: string;
  original_filename: string;
  size_bytes: number;
  sha256: string;
  staged_at: string;
  committed_at: string | null;
}

export interface Violation {
  rule: string;
  row: number | null;
  column: string | null;
  message_en: string;
  message_ar: string;
}

export interface UploadPreview {
  upload: StagedUpload;
  row_count: number;
  columns_present: string[];
  columns_missing: string[];
  columns_unexpected: string[];
  /** Blocks the commit. The file is wrong. */
  rejects: Violation[];
  /** Loads, and surfaces on the Data Quality page. The data has a problem. */
  exceptions: Violation[];
  can_commit: boolean;
  /** SUGGESTED from the file's date range — never applied. The human confirms. */
  suggested_coverage_start: string | null;
  suggested_coverage_end: string | null;
  coverage_required: boolean;
  history_required: boolean;
}

export interface CommitDeclaration {
  coverage_start?: string | null;
  coverage_end?: string | null;
  history_since?: string | null;
}

export interface RefreshReport {
  status: string;
  return_code: number;
  stdout: string;
  stderr: string;
  execution_time_seconds: number;
}

export interface DomainStatus {
  domain: string;
  label_en: string;
  label_ar: string;
  kind: string;
  contracted: boolean;
  declared: boolean;
  provided: boolean;
  row_count: number;
  coverage_start: string | null;
  coverage_end: string | null;
  covered_days: number | null;
  expected_days: number | null;
  history_since: string | null;
  available: boolean;
  unavailable_reason: string | null;
}

export interface OnboardingStatus {
  data_mode: string;
  report_month: string | null;
  domains: DomainStatus[];
}

export function stageUpload(table: string, file: File): Promise<StagedUpload> {
  const form = new FormData();
  form.append('file', file);
  // The table is a PARAMETER. It used to be read off the filename, so
  // payroll.csv renamed employees.csv replaced the employee master - which is
  // why the old UI renamed files client-side before sending them.
  return postForm<StagedUpload>(
    `/api/data/uploads?table=${encodeURIComponent(table)}`, form);
}

export function previewUpload(uploadId: string): Promise<UploadPreview> {
  return getJson<UploadPreview>(`/api/data/uploads/${uploadId}`);
}

export function commitUpload(
  uploadId: string,
  declaration: CommitDeclaration,
): Promise<RefreshReport> {
  return postJson<RefreshReport>(
    `/api/data/uploads/${uploadId}/commit`, declaration);
}

export function discardUpload(uploadId: string): Promise<void> {
  return del<void>(`/api/data/uploads/${uploadId}`);
}

export function listUploads(): Promise<StagedUpload[]> {
  return getJson<StagedUpload[]>('/api/data/uploads');
}

export function fetchOnboardingStatus(): Promise<OnboardingStatus> {
  return getJson<OnboardingStatus>('/api/data/onboarding-status');
}

/**
 * The error report the user opens NEXT TO their spreadsheet.
 *
 * The fix happens in Excel, not in a browser tab, so this is the artefact that
 * survives the context switch — and the only one that can be handed to whoever
 * owns the source system.
 *
 * `totalRejects` / `totalExceptions` are the TRUE totals. The validator stops
 * rendering at 100 (MAX_RENDERED_VIOLATIONS), so a report that silently showed
 * 100 rows would send the user round the fix-and-retry loop repeatedly. When
 * the list is capped, the report says so on its own line. Raising the cap is a
 * validator change and is deliberately not done here.
 */
export const RENDERED_VIOLATION_CAP = 100;

function csvCell(value: unknown): string {
  const text = value === null || value === undefined ? '' : String(value);
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export function buildErrorReport(preview: UploadPreview): string {
  const header = [
    'severity', 'row', 'column', 'rule', 'message_en', 'message_ar',
  ];
  const lines = [header.join(',')];

  const push = (severity: string, violations: Violation[]) => {
    for (const v of violations) {
      lines.push([
        severity, v.row ?? '', v.column ?? '', v.rule,
        v.message_en, v.message_ar,
      ].map(csvCell).join(','));
    }
  };
  push('REJECT', preview.rejects);
  push('EXCEPTION', preview.exceptions);

  const shown = preview.rejects.length + preview.exceptions.length;
  if (preview.rejects.length >= RENDERED_VIOLATION_CAP
      || preview.exceptions.length >= RENDERED_VIOLATION_CAP) {
    lines.push('');
    lines.push(csvCell(
      `NOTE: the validator reports at most ${RENDERED_VIOLATION_CAP} violations `
      + `per severity. ${shown} are listed here and there may be more. Fix `
      + `these and re-upload to see the next batch.`));
  }
  return lines.join('\r\n') + '\r\n';
}

export function errorReportFilename(preview: UploadPreview): string {
  const stamp = preview.upload.staged_at.replace(/[:T]/g, '-').slice(0, 16);
  return `${preview.upload.table}-validation-errors-${stamp}.csv`;
}

/** Violations grouped by column — the shape of the fix.
 *  A user opens one column and fixes it; they do not walk 43 unrelated rows. */
export interface ColumnGroup {
  column: string;
  count: number;
  rule: string;
  rows: number[];
  example: Violation;
}

export function groupByColumn(violations: Violation[]): ColumnGroup[] {
  const groups = new Map<string, ColumnGroup>();
  for (const v of violations) {
    const key = v.column ?? '(row)';
    const existing = groups.get(key);
    if (existing) {
      existing.count += 1;
      if (v.row !== null) existing.rows.push(v.row);
    } else {
      groups.set(key, {
        column: key,
        count: 1,
        rule: v.rule,
        rows: v.row !== null ? [v.row] : [],
        example: v,
      });
    }
  }
  return Array.from(groups.values()).sort((a, b) => b.count - a.count);
}
