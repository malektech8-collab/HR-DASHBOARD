import { describe, expect, it } from 'vitest';

import { aMapping, aPreview, aViolation } from '../test/builders';
import { commitGate, isDeclarationReady } from './uploadFlow';
import type { CommitDeclaration, UploadPreview } from './uploads';

/**
 * The two rules that decide whether a client's upload may be committed.
 *
 * Tested as a truth table rather than through the DOM, by ruling: they either
 * BLOCK A VALID COMMIT or ADMIT BAD DATA, and driving a form once per
 * combination would cover fewer of them, more slowly, while asserting on
 * markup that is going to change.
 */

const NOTHING_REQUIRED = aPreview();
const COVERAGE = aPreview({ coverage_required: true });
const HISTORY = aPreview({ history_required: true });
const BOTH = aPreview({ coverage_required: true, history_required: true });

const NO_DATES: CommitDeclaration = {
  coverage_start: null, coverage_end: null, history_since: null };
const COVERAGE_DATES: CommitDeclaration = {
  coverage_start: '2026-08-01', coverage_end: '2026-08-07', history_since: null };
const HISTORY_DATE: CommitDeclaration = {
  coverage_start: null, coverage_end: null, history_since: '2024-01-15' };
const ALL_DATES: CommitDeclaration = {
  coverage_start: '2026-08-01', coverage_end: '2026-08-07',
  history_since: '2024-01-15' };

describe('isDeclarationReady — the truth table', () => {
  // requirement            dates supplied    confirmed   ready
  const table: Array<[string, UploadPreview, CommitDeclaration, boolean, boolean]> = [
    ['nothing required, nothing given, unconfirmed', NOTHING_REQUIRED, NO_DATES, false, true],
    ['nothing required, nothing given, confirmed',   NOTHING_REQUIRED, NO_DATES, true,  true],

    ['coverage required, no dates, unconfirmed',     COVERAGE, NO_DATES,       false, false],
    ['coverage required, no dates, confirmed',       COVERAGE, NO_DATES,       true,  false],
    ['coverage required, dates, UNCONFIRMED',        COVERAGE, COVERAGE_DATES, false, false],
    ['coverage required, dates, confirmed',          COVERAGE, COVERAGE_DATES, true,  true],
    ['coverage required, only a start date',         COVERAGE,
      { ...NO_DATES, coverage_start: '2026-08-01' },                           true,  false],
    ['coverage required, only an end date',          COVERAGE,
      { ...NO_DATES, coverage_end: '2026-08-07' },                             true,  false],

    ['history required, no date, confirmed',         HISTORY, NO_DATES,        true,  false],
    ['history required, date, UNCONFIRMED',          HISTORY, HISTORY_DATE,    false, false],
    ['history required, date, confirmed',            HISTORY, HISTORY_DATE,    true,  true],

    ['both required, coverage only, confirmed',      BOTH, COVERAGE_DATES,     true,  false],
    ['both required, history only, confirmed',       BOTH, HISTORY_DATE,       true,  false],
    ['both required, all dates, UNCONFIRMED',        BOTH, ALL_DATES,          false, false],
    ['both required, all dates, confirmed',          BOTH, ALL_DATES,          true,  true],
  ];

  it.each(table)('%s -> %s', (_name, preview, declaration, confirmed, expected) => {
    expect(isDeclarationReady(preview, { declaration, confirmed })).toBe(expected);
  });

  it('a pre-filled but UNCONFIRMED declaration is not a declaration', () => {
    // Category F ruling 3, in one assertion. The page fills these fields from
    // the file's date range, so "the dates are present" says nothing about
    // whether a human agreed with them.
    expect(isDeclarationReady(COVERAGE,
      { declaration: COVERAGE_DATES, confirmed: false })).toBe(false);
    expect(isDeclarationReady(COVERAGE,
      { declaration: COVERAGE_DATES, confirmed: true })).toBe(true);
  });

  it('no preview means nothing to declare', () => {
    expect(isDeclarationReady(null, { declaration: NO_DATES, confirmed: false })).toBe(true);
  });
});

describe('commitGate — REJECT blocks, EXCEPTION permits and is announced', () => {
  const ready = { declaration: ALL_DATES, confirmed: true };

  it('a clean preview commits', () => {
    const gate = commitGate(NOTHING_REQUIRED, ready, false);
    expect(gate.enabled).toBe(true);
    expect(gate.label).toBe('Commit');
    expect(gate.blockedBecause).toBeNull();
  });

  it('a REJECT blocks, and the reason names the count', () => {
    const gate = commitGate(
      aPreview({ can_commit: false, rejects: [aViolation(), aViolation()] }),
      ready, false);
    expect(gate.enabled).toBe(false);
    expect(gate.blockedBecause).toBe('2 errors must be fixed before this can be committed.');
  });

  it('one REJECT reads in the singular', () => {
    const gate = commitGate(
      aPreview({ can_commit: false, rejects: [aViolation()] }), ready, false);
    expect(gate.blockedBecause).toBe('1 error must be fixed before this can be committed.');
  });

  it('EXCEPTIONS do NOT block, and the label carries the consequence', () => {
    const gate = commitGate(
      aPreview({ exceptions: [aViolation(), aViolation(), aViolation()] }),
      ready, false);
    expect(gate.enabled).toBe(true);
    expect(gate.label).toBe('Commit — 3 data-quality exceptions will be recorded');
  });

  it('one exception reads in the singular', () => {
    const gate = commitGate(aPreview({ exceptions: [aViolation()] }), ready, false);
    expect(gate.label).toBe('Commit — 1 data-quality exception will be recorded');
  });

  it('REJECT wins over EXCEPTION: the label still warns, the button still blocks', () => {
    const gate = commitGate(
      aPreview({ can_commit: false, rejects: [aViolation()], exceptions: [aViolation()] }),
      ready, false);
    expect(gate.enabled).toBe(false);
    expect(gate.label).toContain('will be recorded');
  });

  it('an unconfirmed declaration blocks a file that is otherwise fine', () => {
    const gate = commitGate(COVERAGE,
      { declaration: COVERAGE_DATES, confirmed: false }, false);
    expect(gate.enabled).toBe(false);
    expect(gate.blockedBecause).toBe('Confirm the period above to continue.');
  });

  it('a commit in flight blocks without claiming anything is wrong', () => {
    const gate = commitGate(NOTHING_REQUIRED, ready, true);
    expect(gate.enabled).toBe(false);
    expect(gate.blockedBecause).toBeNull();
  });

  it('no preview cannot be committed', () => {
    expect(commitGate(null, ready, false).enabled).toBe(false);
  });
});


/**
 * THE DEFECT THIS SECTION EXISTS FOR, precisely.
 *
 *   Cycle A widened `can_commit` to also block on unmapped headers and
 *   unmapped REJECT-enum values. `commitGate` was not told, and still read the
 *   reason off `preview.rejects.length`. With a clean file and an incomplete
 *   profile that produced:
 *
 *       "0 errors must be fixed before this can be committed."
 *
 *   It failed closed, so nothing wrong was committed. It was simply a dead
 *   end: the count was zero, the cause was elsewhere, and `MappingOut` — which
 *   named the cause exactly — was returned by the preview and read by nothing.
 *
 * So the gate now derives the reason instead of assuming it, and returns it as
 * a value the page can branch on rather than a sentence it can only print.
 */
describe('commitGate — why it is blocked', () => {
  const ready = { declaration: {}, confirmed: false };

  it('never says "0 errors" when the blocker is the mapping', () => {
    const preview = aPreview({
      can_commit: false,
      mapping: aMapping({ unmapped: ['ملاحظات'] }),
    });
    const gate = commitGate(preview, ready, false);

    expect(gate.blockedBecause).not.toContain('0 errors');
    expect(gate.blockKind).toBe('unmapped-columns');
    expect(gate.blockCount).toBe(1);
  });

  it('names unmapped values, and counts them across columns', () => {
    const preview = aPreview({
      can_commit: false,
      mapping: aMapping({
        unmapped_values: { status: ['معلق', 'منتهي'], end_of_service_type: ['فصل'] },
      }),
    });
    const gate = commitGate(preview, ready, false);

    expect(gate.blockKind).toBe('unmapped-values');
    expect(gate.blockCount).toBe(3);
  });

  it('puts rejects ahead of the mapping when both apply', () => {
    // Fixing the file is the more actionable step. A client sent to the
    // mapping screen who then still cannot commit has been sent twice.
    const preview = aPreview({
      can_commit: false,
      rejects: [aViolation()],
      mapping: aMapping({ unmapped: ['ملاحظات'] }),
    });

    expect(commitGate(preview, ready, false).blockKind).toBe('rejects');
  });

  it('stays vague rather than confident about a cause it did not check', () => {
    // A future server-side blocker this client does not model must not be
    // reported as something it is not.
    const preview = aPreview({ can_commit: false, mapping: aMapping() });
    const gate = commitGate(preview, ready, false);

    expect(gate.enabled).toBe(false);
    expect(gate.blockedBecause).not.toContain('0');
  });

  it('falls through to the declaration once the mapping is complete', () => {
    const preview = aPreview({
      can_commit: true,
      coverage_required: true,
      mapping: aMapping(),
    });

    expect(commitGate(preview, ready, false).blockKind).toBe('declaration');
  });

  it('enables with no blockKind when everything is satisfied', () => {
    const gate = commitGate(aPreview({ mapping: aMapping() }), ready, false);

    expect(gate.enabled).toBe(true);
    expect(gate.blockKind).toBeNull();
  });

  it('reports busy separately, with nothing to say', () => {
    const gate = commitGate(aPreview({ mapping: aMapping() }), ready, true);

    expect(gate.blockKind).toBe('busy');
    expect(gate.blockedBecause).toBeNull();
  });

  it('handles a preview with no mapping at all', () => {
    // A client whose export is already canonical has `mapping: null`.
    const gate = commitGate(aPreview({ mapping: null }), ready, false);

    expect(gate.enabled).toBe(true);
  });
});
