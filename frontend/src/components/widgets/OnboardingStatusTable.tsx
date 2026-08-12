import React from 'react';
import { CheckCircle2, Lock, Upload } from 'lucide-react';

import { CoverageNote } from '../ui/CoverageNote';
import { NotProvided } from '../ui/NotProvided';
import type { DomainStatus, OnboardingStatus } from '../../lib/uploads';
import type { CoverageItem } from '../../lib/types';

/**
 * The screen that makes partial onboarding legible instead of confusing.
 *
 * It reuses `NotProvided` and `CoverageNote` deliberately: the onboarding
 * checklist should explain the dashboard's blanks in the dashboard's own
 * words. A second component saying "not provided" differently would be the
 * third parallel implementation this project keeps removing.
 *
 * The copy reads as progress through a checklist, not as a broken product. A
 * client mid-onboarding will see mostly grey, and that is the truth — but grey
 * that says "next step" lands very differently from grey that says "missing".
 */

function coverageItem(domain: DomainStatus): CoverageItem | null {
  if (domain.covered_days === null || domain.expected_days === null) return null;
  if (domain.covered_days >= domain.expected_days) return null;
  const window = domain.coverage_start && domain.coverage_end
    ? ` (${domain.coverage_start} to ${domain.coverage_end})` : '';
  return {
    domain: domain.domain,
    domain_label_en: domain.label_en,
    domain_label_ar: domain.label_ar,
    declared_start: domain.coverage_start,
    declared_end: domain.coverage_end,
    covered_days: domain.covered_days,
    expected_days: domain.expected_days,
    coverage_pct: domain.expected_days
      ? Math.round((1000 * domain.covered_days) / domain.expected_days) / 10 : 0,
    message_en: `Covers ${domain.covered_days} of ${domain.expected_days} working days${window}.`,
    message_ar: `يغطي ${domain.covered_days} من ${domain.expected_days} يوم عمل${window}.`,
  };
}

interface Props {
  status: OnboardingStatus;
  onUpload?: (domain: string) => void;
}

export const OnboardingStatusTable: React.FC<Props> = ({ status, onUpload }) => {
  const provided = status.domains.filter((d) => d.provided && d.contracted);
  const contracted = status.domains.filter((d) => d.contracted);

  return (
    <div className="space-y-4" data-testid="onboarding-status">
      <div className="flex items-baseline justify-between">
        <h3 className="text-lg font-bold">Onboarding progress</h3>
        <p className="text-xs text-muted-foreground">
          {provided.length} of {contracted.length} domains provided
          {status.report_month ? ` · reporting period ${status.report_month}` : ''}
        </p>
      </div>

      <div className="space-y-3">
        {status.domains.map((domain) => {
          const coverage = coverageItem(domain);

          if (!domain.available) {
            return (
              <div
                key={domain.domain}
                className="border border-border rounded-lg p-4 bg-muted/20 opacity-70"
              >
                <div className="flex items-center gap-2">
                  <Lock className="w-4 h-4 text-muted-foreground" />
                  <span className="font-semibold text-sm">{domain.label_en}</span>
                  <span className="text-xs text-muted-foreground">{domain.label_ar}</span>
                </div>
                {/* Not "missing" — it cannot be provided at all, and a client
                    shown "missing" will keep trying to upload it. */}
                <p className="text-xs text-muted-foreground mt-2">
                  {domain.unavailable_reason}
                </p>
              </div>
            );
          }

          if (!domain.provided) {
            return (
              <div key={domain.domain} className="border border-border rounded-lg p-4">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm">{domain.label_en}</span>
                    <span className="text-xs text-muted-foreground">{domain.label_ar}</span>
                  </div>
                  <button
                    onClick={() => onUpload?.(domain.domain)}
                    className="px-3 py-1.5 bg-primary text-primary-foreground text-xs font-semibold rounded-lg hover:opacity-90 flex items-center gap-1.5"
                  >
                    <Upload className="w-3.5 h-3.5" /> Upload
                  </button>
                </div>
                {/* The same component the dashboard uses for the same fact. */}
                <div className="mt-3">
                  <NotProvided
                    title={domain.label_en}
                    items={[]}
                    variant="panel"
                  />
                </div>
              </div>
            );
          }

          return (
            <div key={domain.domain} className="border border-border rounded-lg p-4">
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-healthy" />
                  <span className="font-semibold text-sm">{domain.label_en}</span>
                  <span className="text-xs text-muted-foreground">{domain.label_ar}</span>
                </div>
                <div className="text-xs text-muted-foreground">
                  {domain.row_count.toLocaleString()} rows
                  {domain.history_since ? ` · history since ${domain.history_since}` : ''}
                </div>
              </div>
              {coverage && (
                <div className="mt-3">
                  <CoverageNote items={[coverage]} variant="banner" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {status.data_mode !== 'real' && (
        <p className="text-xs text-muted-foreground">
          Demo mode: every domain is served from sample data, so all of them
          report as provided.
        </p>
      )}
    </div>
  );
};
