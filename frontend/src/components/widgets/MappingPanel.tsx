import React, { useState } from 'react';
import { ArrowRight, ChevronDown, ChevronRight, Wand2 } from 'lucide-react';

import type { MappingSummary } from '../../lib/uploads';

/**
 * What the mapping profile did, and what it still needs.
 *
 * Cycle A returned all of this on the preview and rendered none of it, so the
 * commit button reported "0 errors must be fixed" whenever the real blocker
 * was an incomplete profile. It failed closed and was unworkable.
 *
 * The split is deliberate. What the profile DID is collapsed: on a working
 * profile it is 22 correct renames nobody needs to read. What still needs a
 * DECISION is always open, because it is the only thing standing between the
 * client and a commit.
 */

const Row: React.FC<{ from: string; to: string }> = ({ from, to }) => (
  <li className="flex items-center gap-2 text-xs">
    <span className="font-mono">{from}</span>
    <ArrowRight className="w-3 h-3 text-muted-foreground shrink-0" />
    <span className="font-mono text-muted-foreground">{to}</span>
  </li>
);

export const MappingPanel: React.FC<{
  mapping: MappingSummary | null;
  onFix?: (header?: string) => void;
}> = ({ mapping, onFix }) => {
  const [open, setOpen] = useState(false);
  if (!mapping || !mapping.applied) return null;

  const renamed = Object.entries(mapping.renamed);
  const valueTasks = Object.entries(mapping.unmapped_values);
  const outstanding = mapping.unmapped.length + valueTasks.length;

  return (
    <section className="border border-border rounded-xl p-4 space-y-3" data-testid="mapping-panel">
      <header className="flex items-center gap-2">
        <Wand2 className="w-4 h-4 text-primary" />
        <h4 className="text-sm font-bold">
          Your column names were mapped
          {mapping.profile_version !== null && (
            <span className="font-normal text-muted-foreground">
              {' '}(profile v{mapping.profile_version})
            </span>
          )}
        </h4>
      </header>

      {mapping.header_changed && (
        <p className="text-xs text-warning" data-testid="header-changed">
          This export's columns differ from the ones this profile was written
          for. Nothing was re-mapped automatically — check the mapping before
          committing.
        </p>
      )}

      {outstanding === 0 ? (
        <p className="text-xs text-muted-foreground">
          Every column has a decision. Nothing here is blocking the upload.
        </p>
      ) : (
        <div className="space-y-3">
          {mapping.unmapped.length > 0 && (
            <div className="space-y-1.5" data-testid="unmapped-columns">
              <p className="text-xs font-semibold text-critical">
                {mapping.unmapped.length} {mapping.unmapped.length === 1
                  ? 'column has' : 'columns have'} no decision yet
              </p>
              <p className="text-xs text-muted-foreground">
                Map each one to a field, or mark it as not needed. Columns are
                never dropped automatically — a renamed export would lose one
                silently.
              </p>
              <ul className="flex flex-wrap gap-1.5">
                {mapping.unmapped.map((header) => (
                  <li key={header}>
                    <button
                      onClick={() => onFix?.(header)}
                      className="px-2 py-1 rounded border border-critical/40 text-xs font-mono hover:bg-critical/10"
                    >
                      {header}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {valueTasks.map(([column, values]) => (
            <div key={column} className="space-y-1.5" data-testid={`unmapped-values-${column}`}>
              <p className="text-xs font-semibold text-critical">
                {values.length} value{values.length === 1 ? '' : 's'} in{' '}
                <span className="font-mono">{column}</span> have no equivalent
              </p>
              {mapping.reject_enum_consequences[column] && (
                <p className="text-xs text-muted-foreground">
                  {mapping.reject_enum_consequences[column]}
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                Your words: <span className="font-mono">{values.join(', ')}</span>
                {' · '}
                Choose from:{' '}
                <span className="font-mono">
                  {(mapping.reject_enum_options[column] ?? []).join(', ')}
                </span>
              </p>
            </div>
          ))}

          {onFix && (
            <button
              onClick={() => onFix()}
              className="px-3 py-1.5 bg-primary text-primary-foreground text-xs font-semibold rounded-lg"
              data-testid="open-mapping"
            >
              Fix the mapping
            </button>
          )}
        </div>
      )}

      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
      >
        {open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        {renamed.length} renamed, {mapping.ignored.length} ignored,{' '}
        {mapping.derived.length} derived
      </button>
      {open && (
        <div className="grid md:grid-cols-2 gap-4 border-t border-border pt-3">
          <ul className="space-y-1">
            {renamed.map(([from, to]) => <Row key={from} from={from} to={to} />)}
          </ul>
          <div className="space-y-2 text-xs">
            {mapping.ignored.length > 0 && (
              <div>
                <p className="text-muted-foreground">Ignored</p>
                <p className="font-mono">{mapping.ignored.join(', ')}</p>
              </div>
            )}
            {mapping.derived.length > 0 && (
              <div>
                <p className="text-muted-foreground">Derived from your data</p>
                <p className="font-mono">{mapping.derived.join(', ')}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
};
