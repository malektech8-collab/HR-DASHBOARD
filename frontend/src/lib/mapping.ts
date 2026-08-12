/**
 * The mapping workspace: the client's own columns, and what they decide.
 *
 * Types mirror the Pydantic models in backend/app/api/data.py exactly.
 *
 * ONE RULE GOVERNS THIS WHOLE MODULE. `SourceColumn.samples` holds the
 * client's own values, read from the staged file at request time so a human
 * can tell what a column actually is. They are shown and then dropped. They
 * are never sent back in a save, never stored, never logged — a profile
 * accumulates as training substrate and outlives the upload, which is why the
 * backend refuses to persist them for any column that is not a vocabulary.
 */
import { getJson, postJson } from './http';

export interface MappingCandidate {
  canonical: string;
  /** Which rung of the ladder matched: canonical | label_exact |
   *  label_normalised | alias. Recorded so accumulated profiles are trainable. */
  matched_by: string;
  confidence: number | null;
}

export interface CanonicalColumn {
  name: string;
  label_en: string;
  label_ar: string;
  required: boolean;
  allowed_values: string[] | null;
}

export interface SourceColumn {
  header: string;
  /** DISPLAY ONLY. Never persisted, never returned to the server. */
  samples: string[];
  non_empty: number;
  candidates: MappingCandidate[];
  current: string | null;
  decision: 'mapped' | 'ignored' | 'undecided';
}

export interface MappingWorkspace {
  upload_id: string;
  table: string;
  row_count: number;
  source_columns: SourceColumn[];
  canonical_columns: CanonicalColumn[];
  reject_enum_options: Record<string, string[]>;
  reject_enum_consequences: Record<string, string>;
  derivation_rules: string[];
  profile_version: number | null;
}

export interface MappingDecision {
  header: string;
  decision: 'mapped' | 'ignored' | 'undecided';
  chosen: string | null;
  reason: string | null;
}

export interface SaveMappingRequest {
  upload_id: string;
  decisions: MappingDecision[];
  values: Record<string, Record<string, string>>;
  derive: Record<string, { rule: string; from: string }>;
  /** Restated pairs — the affirmation. `confirmed_by` comes from the session. */
  confirmations: Record<string, Record<string, string>>;
}

export interface SavedMapping {
  table: string;
  version: number;
  created_by: string;
  created_at: string;
  mapped: number;
  ignored: number;
  undecided: number;
}

export function fetchWorkspace(uploadId: string): Promise<MappingWorkspace> {
  return getJson<MappingWorkspace>(`/api/data/uploads/${uploadId}/columns`);
}

export function saveMapping(
  table: string, body: SaveMappingRequest,
): Promise<SavedMapping> {
  return postJson<SavedMapping>(`/api/data/mapping/${table}`, body);
}

/**
 * Pre-selection, and the asymmetry it rests on.
 *
 * Rungs 1–3 come from the contract's own labels, so they are pre-selected: on
 * a well-formed export that decides 20 of 24 columns and leaves the human the
 * ones that actually need judgement. Rung 4 (the hand-seeded alias table) is a
 * curated guess and is offered without being taken.
 *
 * A wrong HEADER mapping usually fails validation loudly. A wrong VALUE
 * mapping into a REJECT enum is silent — which is why that one needs a tick
 * and this does not.
 */
export function preselect(column: SourceColumn): string | null {
  if (column.current) return column.current;
  const best = column.candidates[0];
  if (!best) return null;
  return best.matched_by === 'alias' ? null : best.canonical;
}

/** Unmapped first: never a 37-row list with the 3 that matter in the middle. */
export function orderForReview(columns: SourceColumn[]): SourceColumn[] {
  const rank = (c: SourceColumn) =>
    (c.decision === 'undecided' && !preselect(c) ? 0 : c.decision === 'undecided' ? 1 : 2);
  return [...columns].sort((a, b) => rank(a) - rank(b));
}

export interface MappingProgress {
  total: number;
  decided: number;
  needAttention: number;
  /** "14 of 37 mapped, 3 need attention" — not a percentage. A percentage
   *  tells you how you are doing; this tells you what is left. */
  label: string;
}

export function progressOf(
  columns: SourceColumn[], chosen: Record<string, string | null>,
  ignored: Record<string, boolean>,
): MappingProgress {
  const total = columns.length;
  let decided = 0;
  for (const column of columns) {
    if (ignored[column.header] || chosen[column.header]) decided += 1;
  }
  const needAttention = total - decided;
  return {
    total,
    decided,
    needAttention,
    label: needAttention === 0
      ? `${decided} of ${total} decided`
      : `${decided} of ${total} decided, ${needAttention} need attention`,
  };
}

/**
 * Which value mappings still need an affirmation.
 *
 * Keyed by the PAIR, not the column — an affirmation given for one pair says
 * nothing about a pair added afterwards, and the backend enforces the same
 * rule at both save and load. This exists so the button can be disabled before
 * the request rather than after the 400.
 */
export function unaffirmedPairs(
  values: Record<string, Record<string, string>>,
  confirmations: Record<string, Record<string, string>>,
  gatedColumns: string[],
): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const column of gatedColumns) {
    const pairs = values[column];
    if (!pairs) continue;
    const affirmed = confirmations[column] ?? {};
    const missing = Object.keys(pairs).filter((k) => affirmed[k] !== pairs[k]);
    if (missing.length > 0) out[column] = missing;
  }
  return out;
}
