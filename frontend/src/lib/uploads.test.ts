/**
 * The error report and the by-column view, from the client's side.
 *
 * These two functions produce the only artefact that leaves the product: the
 * CSV a client opens beside their spreadsheet, and the list they work down.
 * Once a mapping profile renames their headers, a report naming canonical
 * columns describes a file they never made. That is the failure these pin.
 */
import { describe, expect, it } from 'vitest';
import { aPreview, aViolation } from '../test/builders';
import { buildErrorReport, groupByColumn } from './uploads';

const MAPPED = aViolation({
  row: 3,
  column: 'joining_date',
  source_column: 'تاريخ الانضمام',
});

describe('buildErrorReport', () => {
  it('leads with the header the client actually wrote', () => {
    const csv = buildErrorReport(aPreview({ rejects: [MAPPED] }));
    const [header, first] = csv.trim().split('\r\n');

    expect(header).toBe(
      'severity,row,your_column,canonical_column,rule,message_en,message_ar');
    // their header in `your_column`, ours kept beside it - a client forwards
    // this to whoever owns the source system, who needs both names.
    expect(first.startsWith('REJECT,3,تاريخ الانضمام,joining_date,')).toBe(true);
  });

  it('falls back to the canonical column when no profile renamed it', () => {
    const csv = buildErrorReport(
      aPreview({ rejects: [aViolation({ row: 3, source_column: null })] }));
    const first = csv.trim().split('\r\n')[1];

    // NOT an empty your_column: with no profile, the canonical name IS the
    // name they wrote.
    expect(first.startsWith('REJECT,3,joining_date,joining_date,')).toBe(true);
  });
});

describe('groupByColumn', () => {
  it('groups by the client\'s header, not the canonical one', () => {
    const groups = groupByColumn([MAPPED, aViolation({ ...MAPPED, row: 9 })]);

    expect(groups).toHaveLength(1);
    expect(groups[0].column).toBe('تاريخ الانضمام');
    expect(groups[0].count).toBe(2);
  });

  it('does not merge two source columns that map to one canonical column', () => {
    // A real export can carry a duplicate. Grouping on the canonical name
    // would hide which of their two columns is the broken one.
    const groups = groupByColumn([
      MAPPED,
      aViolation({ row: 4, column: 'joining_date', source_column: 'تاريخ التعيين' }),
    ]);

    expect(groups.map((g) => g.column).sort())
      .toEqual(['تاريخ الانضمام', 'تاريخ التعيين']);
  });
});
