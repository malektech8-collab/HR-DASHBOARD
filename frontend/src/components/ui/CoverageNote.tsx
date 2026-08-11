import React from 'react';
import { CalendarRange } from 'lucide-react';
import type { CoverageItem } from '../../lib/types';

/**
 * What sits BESIDE a figure that is real but measured over less than the whole
 * period.
 *
 * Deliberately a different thing from `NotProvided`, in weight and in colour:
 *
 *   NotProvided  replaces content  — "nothing is here yet"
 *   CoverageNote sits beside it    — "this is real, over less than you assume"
 *
 * Conflating them visually would undo at the last step the distinction the API
 * is careful to make: `suppressed` means withheld, `coverage` means qualified.
 * A reader who cannot tell them apart cannot infer absence from a suppression.
 *
 * It renders only when the API sends an item, and the API sends one only when
 * covered < expected — so full coverage is silent. A note on every card trains
 * people to stop reading notes, and that would cost most on the one case that
 * most needs an explanation: the unmeasurable em dash.
 */

export function collectCoverage(
  ...responses: Array<{ coverage_notes?: CoverageItem[] } | null | undefined>
): CoverageItem[] {
  const seen = new Set<string>();
  const out: CoverageItem[] = [];
  for (const response of responses) {
    for (const item of response?.coverage_notes ?? []) {
      if (seen.has(item.domain)) continue;
      seen.add(item.domain);
      out.push(item);
    }
  }
  return out;
}

interface CoverageNoteProps {
  items: CoverageItem[];
  /** `banner` heads a page; `caption` attaches to one chart or KPI strip. */
  variant?: 'banner' | 'caption';
}

export const CoverageNote: React.FC<CoverageNoteProps> = ({
  items,
  variant = 'banner',
}) => {
  if (!items.length) return null;

  if (variant === 'caption') {
    return (
      <p
        data-testid="coverage-caption"
        className="text-xs text-muted-foreground mt-2"
      >
        {items.map((item) => item.message_en).join(' ')}
      </p>
    );
  }

  return (
    <div
      data-testid="coverage-banner"
      className="flex items-start gap-3 rounded-lg border border-warning/20 bg-warning/5 px-4 py-3"
    >
      <CalendarRange className="w-4 h-4 mt-0.5 text-warning shrink-0" />
      <div className="text-sm text-foreground">
        {items.map((item) => (
          <p key={item.domain}>
            <span className="font-semibold">{item.domain_label_en}</span>{' '}
            covers <span className="font-semibold">
              {item.covered_days} of {item.expected_days} working days
            </span>
            {item.declared_start && item.declared_end
              ? ` (${item.declared_start} to ${item.declared_end})`
              : ''}
            . Figures below are measured over those days only.
          </p>
        ))}
      </div>
    </div>
  );
};
