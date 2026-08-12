/**
 * The two rules that decide whether a client's upload may be committed.
 *
 * Extracted from `DataOnboarding.tsx` by ruling: they either **block a valid
 * commit** or **admit bad data**, and a rule with those two failure modes
 * should not be tested by driving a DOM. As pure functions they are a truth
 * table — every combination, in milliseconds, named.
 *
 * Neither is the enforcement. The API refuses a rejected file and a missing
 * declaration regardless (`can_commit` comes from the server, and commit
 * returns 400 without coverage or history). These decide what the *button*
 * does, so a user is never invited to press something that will fail, and is
 * never able to press something that will succeed for the wrong reason.
 */
import type { CommitDeclaration, UploadPreview } from './uploads';

/** Which requirements a preview imposes, and whether they are satisfied. */
export interface DeclarationState {
  declaration: CommitDeclaration;
  /** The user actively confirmed — a ticked box, not a pre-filled field. */
  confirmed: boolean;
}

/**
 * Category F, ruling 3: a suggestion a human confirms is a declaration; a
 * pre-filled field they never look at is inference wearing a costume.
 *
 * So `confirmed` is required whenever anything is required. Filling the dates
 * is not enough, because the page fills them for you.
 */
export function isDeclarationReady(
  preview: UploadPreview | null,
  state: DeclarationState,
): boolean {
  if (!preview) return true;

  const needsCoverage = preview.coverage_required;
  const needsHistory = preview.history_required;
  if (!needsCoverage && !needsHistory) return true;

  const coverageGiven = Boolean(
    state.declaration.coverage_start && state.declaration.coverage_end);
  const historyGiven = Boolean(state.declaration.history_since);

  if (needsCoverage && !coverageGiven) return false;
  if (needsHistory && !historyGiven) return false;
  return state.confirmed;
}

export interface CommitGate {
  enabled: boolean;
  /** Why it is disabled, in the words the page shows. Null when enabled. */
  blockedBecause: string | null;
  /** The button's label — it carries the consequence when exceptions remain. */
  label: string;
}

/**
 * The commit button.
 *
 * REJECT blocks; EXCEPTION permits and is announced. They are not two points
 * on a severity scale — a reject means the file is wrong, an exception means
 * the data has a problem the business already has — and the button is the last
 * place that distinction is visible before the client acts on it.
 */
export function commitGate(
  preview: UploadPreview | null,
  state: DeclarationState,
  busy: boolean,
): CommitGate {
  const exceptions = preview?.exceptions.length ?? 0;
  const label = exceptions > 0
    ? `Commit — ${exceptions} data-quality ${
        exceptions === 1 ? 'exception' : 'exceptions'} will be recorded`
    : 'Commit';

  if (!preview) {
    return { enabled: false, blockedBecause: 'Nothing to commit.', label };
  }
  if (!preview.can_commit) {
    const n = preview.rejects.length;
    return {
      enabled: false,
      blockedBecause: `${n} ${n === 1 ? 'error' : 'errors'} must be fixed before this can be committed.`,
      label,
    };
  }
  if (!isDeclarationReady(preview, state)) {
    return {
      enabled: false,
      blockedBecause: 'Confirm the period above to continue.',
      label,
    };
  }
  if (busy) {
    return { enabled: false, blockedBecause: null, label };
  }
  return { enabled: true, blockedBecause: null, label };
}
