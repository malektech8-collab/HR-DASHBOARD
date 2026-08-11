import React from 'react';
import { Upload } from 'lucide-react';
import type { SuppressionItem } from '../../lib/types';

/**
 * What a page renders instead of a chart when the data was never provided.
 *
 * Phase 2 P0-3, step 2b. The rule this component exists to enforce: a figure
 * the client has not provided is NEVER drawn as zero, and never as an empty
 * chart. An empty chart is a claim that the period had no events; a zero is a
 * claim that the answer is zero. Both are read as measurements.
 *
 * So the space says three things instead: which domain is missing, that it is
 * missing rather than empty, and what to do about it. Onboarding is the state
 * this product spends its first weeks in, and it should look like progress
 * rather than like a broken dashboard.
 */

const DOMAIN_LABELS: Record<string, string> = {
  employees: 'Employees',
  payroll: 'Payroll',
  attendance: 'Attendance',
  compliance: 'Compliance',
  hr_requests: 'HR Requests',
  employee_relations: 'Employee Relations',
  recruitment: 'Recruitment',
  talent: 'Talent',
};

export function collectSuppressions(
  ...responses: Array<{ suppressed?: SuppressionItem[] } | null | undefined>
): SuppressionItem[] {
  const seen = new Set<string>();
  const out: SuppressionItem[] = [];
  for (const response of responses) {
    for (const item of response?.suppressed ?? []) {
      const id = `${item.mart}::${item.key}`;
      if (seen.has(id)) continue;
      seen.add(id);
      out.push(item);
    }
  }
  return out;
}

export function missingDomains(items: SuppressionItem[]): string[] {
  const domains = new Set<string>();
  for (const item of items) {
    for (const domain of item.missing_domains) domains.add(domain);
  }
  return Array.from(domains).sort();
}

interface NotProvidedProps {
  /** What the reader came here to see, e.g. "Attendance". */
  title: string;
  /** The suppression entries the API sent alongside the null. */
  items: SuppressionItem[];
  /** `page` fills the view; `panel` sits in a chart's place. */
  variant?: 'page' | 'panel';
}

export const NotProvided: React.FC<NotProvidedProps> = ({
  title,
  items,
  variant = 'page',
}) => {
  const domains = missingDomains(items);
  const labels = domains.map((d) => DOMAIN_LABELS[d] ?? d);
  const unmapped = items.some((i) => i.reason === 'not_mapped');

  const heading =
    labels.length > 0
      ? `${title} needs ${labels.join(', ')}`
      : `${title} is not available`;

  const explanation = unmapped
    ? 'This figure has no declared data source, so it cannot be attributed to anything you uploaded.'
    : 'Nothing here is estimated or defaulted while the data is missing — the figures appear once the file is uploaded.';

  return (
    <div
      data-testid="not-provided"
      className={
        variant === 'page'
          ? 'border border-dashed border-border rounded-xl p-10 text-center my-10 bg-muted/20'
          : 'border border-dashed border-border rounded-lg p-8 text-center bg-muted/10 h-full flex flex-col items-center justify-center'
      }
    >
      <Upload className="w-8 h-8 mx-auto mb-3 text-muted-foreground" />
      <h3 className="text-base font-bold text-foreground">{heading}</h3>
      <p className="text-sm text-muted-foreground mt-2 max-w-md mx-auto">
        {explanation}
      </p>

      {labels.length > 0 && (
        <div className="flex flex-wrap gap-2 justify-center mt-4">
          {labels.map((label) => (
            <span
              key={label}
              className="px-3 py-1 rounded-full text-xs font-semibold bg-warning/10 text-warning border border-warning/20"
            >
              {label} — not yet provided
            </span>
          ))}
        </div>
      )}

      {items.length > 0 && (
        <details className="mt-5 text-left inline-block">
          <summary className="text-xs font-semibold text-muted-foreground cursor-pointer">
            {items.length} withheld {items.length === 1 ? 'figure' : 'figures'}
          </summary>
          <ul className="mt-2 space-y-1">
            {items.map((item) => (
              <li
                key={`${item.mart}::${item.key}`}
                className="text-xs text-muted-foreground"
              >
                <span className="font-mono">{item.key}</span> — {item.message_en}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
};
