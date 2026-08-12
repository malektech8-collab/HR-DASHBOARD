/**
 * The mapping screen's rules, as pure functions.
 *
 * Pre-selection, ordering and the affirmation check all decide what a human
 * is asked and what they are not. Getting them wrong either buries the three
 * columns that need attention in a list of 24, or quietly accepts a value
 * mapping nobody affirmed. Neither is something to verify by driving a DOM.
 */
import { describe, expect, it } from 'vitest';
import {
  orderForReview,
  preselect,
  progressOf,
  unaffirmedPairs,
} from './mapping';
import type { SourceColumn } from './mapping';

function aColumn(over: Partial<SourceColumn> = {}): SourceColumn {
  return {
    header: 'الجنسيه',
    samples: ['سعودي', 'مصري'],
    non_empty: 3,
    candidates: [{
      canonical: 'nationality', matched_by: 'label_normalised', confidence: 0.85,
    }],
    current: null,
    decision: 'undecided',
    ...over,
  };
}

describe('preselect', () => {
  it('takes a contract-derived match', () => {
    expect(preselect(aColumn())).toBe('nationality');
  });

  it('does NOT take an alias — a curated guess is offered, not applied', () => {
    const column = aColumn({
      candidates: [{ canonical: 'employee_name', matched_by: 'alias', confidence: 0.7 }],
    });
    expect(preselect(column)).toBeNull();
  });

  it('prefers what the existing profile already decided', () => {
    // A saved mapping is a human's past decision; a suggestion is not, so the
    // suggestion must never silently overwrite it on a re-open.
    const column = aColumn({ current: 'job_title' });
    expect(preselect(column)).toBe('job_title');
  });

  it('is null when nothing matched', () => {
    expect(preselect(aColumn({ candidates: [] }))).toBeNull();
  });
});

describe('orderForReview', () => {
  it('puts the columns needing a human first', () => {
    const decided = aColumn({ header: 'decided', decision: 'mapped', current: 'nationality' });
    const suggested = aColumn({ header: 'suggested' });
    const blank = aColumn({ header: 'blank', candidates: [] });

    expect(orderForReview([decided, suggested, blank]).map((c) => c.header))
      .toEqual(['blank', 'suggested', 'decided']);
  });

  it('does not mutate the input', () => {
    const columns = [aColumn({ header: 'b', decision: 'mapped', current: 'x' }),
      aColumn({ header: 'a', candidates: [] })];
    orderForReview(columns);
    expect(columns.map((c) => c.header)).toEqual(['b', 'a']);
  });
});

describe('progressOf', () => {
  it('counts what is left, not a percentage', () => {
    const columns = [aColumn({ header: 'a' }), aColumn({ header: 'b' }),
      aColumn({ header: 'c' })];
    const progress = progressOf(columns, { a: 'nationality', b: null, c: null },
      { b: true });

    expect(progress.decided).toBe(2);
    expect(progress.needAttention).toBe(1);
    expect(progress.label).toBe('2 of 3 decided, 1 need attention');
  });

  it('says nothing about attention when there is none', () => {
    const columns = [aColumn({ header: 'a' })];
    expect(progressOf(columns, { a: 'nationality' }, {}).label)
      .toBe('1 of 1 decided');
  });
});

describe('unaffirmedPairs', () => {
  const gated = ['status', 'end_of_service_type'];

  it('reports a pair with no affirmation at all', () => {
    expect(unaffirmedPairs({ status: { 'معلق': 'Active' } }, {}, gated))
      .toEqual({ status: ['معلق'] });
  });

  it('accepts a pair affirmed exactly', () => {
    const pairs = { 'معلق': 'Terminated' };
    expect(unaffirmedPairs({ status: pairs }, { status: { ...pairs } }, gated))
      .toEqual({});
  });

  it('reports only the NEW pair when one is added', () => {
    // Keyed by the pair, not the column: an affirmation given in August must
    // not bless a word that first appeared in September.
    const august = { 'نشط': 'Active' };
    const september = { 'نشط': 'Active', 'منتهي': 'Terminated' };
    expect(unaffirmedPairs({ status: september }, { status: august }, gated))
      .toEqual({ status: ['منتهي'] });
  });

  it('reports a pair whose target changed under an old affirmation', () => {
    expect(unaffirmedPairs(
      { status: { 'معلق': 'Terminated' } },
      { status: { 'معلق': 'Active' } }, gated,
    )).toEqual({ status: ['معلق'] });
  });

  it('ignores a column that is not gated', () => {
    // The eleven EXCEPTION enums take no affirmation, by decision.
    expect(unaffirmedPairs({ contract_type: { 'محدد': 'Limited' } }, {}, gated))
      .toEqual({});
  });
});
