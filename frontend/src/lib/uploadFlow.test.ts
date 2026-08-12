import { describe, expect, it } from 'vitest';

import { aPreview, aViolation } from '../test/builders';
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
