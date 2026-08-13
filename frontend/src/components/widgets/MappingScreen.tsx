import React, { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, ArrowRight, Check, RefreshCw, X } from 'lucide-react';

import {
  fetchWorkspace,
  orderForReview,
  preselect,
  progressOf,
  saveMapping,
  unaffirmedPairs,
  valuesNeedingMapping,
} from '../../lib/mapping';
import type { MappingWorkspace, SourceColumn } from '../../lib/mapping';

/**
 * The mapping screen.
 *
 * Three rules, all settled before this was built:
 *
 *   UNMAPPED FIRST. A 37-row list with the three that matter in the middle is
 *   a list nobody finishes. `orderForReview` puts undecided-and-unsuggested at
 *   the top.
 *
 *   SAMPLE VALUES ARE SHOWN, NEVER SENT BACK. A header alone often will not
 *   settle a mapping, so the client's own values appear beside each column.
 *   They arrive from `GET /uploads/{id}/columns`, are rendered, and are dropped.
 *   The save body carries decisions only.
 *
 *   THE AFFIRMATION IS NEVER PRE-FILLED. A value mapping into a REJECT enum is
 *   silent once applied — `معلق` mapped to Active counts a suspended employee
 *   as employed and nothing downstream can question it. So the tick is keyed to
 *   the pair, states what the mapping decides, and is the client's act alone.
 */

const CONFIDENCE_LABEL: Record<string, string> = {
  canonical: 'exact field name',
  label_exact: 'exact label match',
  label_normalised: 'label match, spelling normalised',
  alias: 'known alias — check this one',
};

const ColumnRow: React.FC<{
  column: SourceColumn;
  chosen: string | null;
  ignored: boolean;
  options: MappingWorkspace['canonical_columns'];
  onChoose: (canonical: string | null) => void;
  onIgnore: (ignored: boolean) => void;
}> = ({ column, chosen, ignored, options, onChoose, onIgnore }) => {
  const best = column.candidates[0];
  return (
    <tr className="border-t border-border align-top" data-testid={`row-${column.header}`}>
      <td className="py-2 pr-3">
        <p className="text-xs font-mono font-semibold">{column.header}</p>
        {/* Their values, for recognition. Shown and forgotten. */}
        <p className="text-xs text-muted-foreground truncate max-w-[16rem]">
          {column.samples.length > 0 ? column.samples.join(' · ') : 'empty in every row'}
        </p>
      </td>
      <td className="py-2 pr-3">
        {best && (
          <span className="text-xs text-muted-foreground">
            {CONFIDENCE_LABEL[best.matched_by] ?? best.matched_by}
            {best.confidence !== null && ` (${Math.round(best.confidence * 100)}%)`}
          </span>
        )}
      </td>
      <td className="py-2 pr-3">
        <select
          value={ignored ? '__ignore' : (chosen ?? '')}
          onChange={(e) => {
            const value = e.target.value;
            if (value === '__ignore') { onIgnore(true); onChoose(null); return; }
            onIgnore(false);
            onChoose(value || null);
          }}
          className="text-xs bg-transparent border border-border rounded px-2 py-1 w-full"
          data-testid={`select-${column.header}`}
        >
          <option value="">— needs a decision —</option>
          <option value="__ignore">Not needed — ignore this column</option>
          {options.map((o) => (
            <option key={o.name} value={o.name}>
              {o.label_en} / {o.label_ar}{o.required ? ' *' : ''}
            </option>
          ))}
        </select>
      </td>
      <td className="py-2 w-6">
        {ignored ? <X className="w-3.5 h-3.5 text-muted-foreground" />
          : chosen ? <Check className="w-3.5 h-3.5 text-healthy" />
            : <AlertTriangle className="w-3.5 h-3.5 text-critical" />}
      </td>
    </tr>
  );
};

export const MappingScreen: React.FC<{
  uploadId: string;
  focusHeader?: string;
  onSaved: () => void;
  onCancel: () => void;
}> = ({ uploadId, focusHeader, onSaved, onCancel }) => {
  const [workspace, setWorkspace] = useState<MappingWorkspace | null>(null);
  const [chosen, setChosen] = useState<Record<string, string | null>>({});
  const [ignored, setIgnored] = useState<Record<string, boolean>>({});
  const [values, setValues] = useState<Record<string, Record<string, string>>>({});
  const [confirmations, setConfirmations] =
    useState<Record<string, Record<string, string>>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchWorkspace(uploadId).then((w) => {
      setWorkspace(w);
      const initialChosen: Record<string, string | null> = {};
      const initialIgnored: Record<string, boolean> = {};
      for (const column of w.source_columns) {
        initialChosen[column.header] = preselect(column);
        initialIgnored[column.header] = column.decision === 'ignored';
      }
      setChosen(initialChosen);
      setIgnored(initialIgnored);
    }).catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [uploadId]);

  const ordered = useMemo(
    () => (workspace ? orderForReview(workspace.source_columns) : []),
    [workspace]);
  const progress = useMemo(
    () => progressOf(workspace?.source_columns ?? [], chosen, ignored),
    [workspace, chosen, ignored]);
  const gated = Object.keys(workspace?.reject_enum_options ?? {});
  const outstanding = unaffirmedPairs(values, confirmations, gated);
  // A gated column whose client words still have no meaning blocks too: saving
  // now would produce a profile the preview immediately rejects.
  const unmeant = (workspace?.source_columns ?? []).some((column) => {
    const canonical = ignored[column.header] ? null : chosen[column.header];
    if (!canonical || !gated.includes(canonical)) return false;
    const options = workspace?.reject_enum_options[canonical] ?? [];
    return valuesNeedingMapping(column, options)
      .some((v) => !values[canonical]?.[v]);
  });
  const blocked = progress.needAttention > 0 || unmeant
    || Object.keys(outstanding).length > 0;

  if (error) {
    return <p className="text-xs text-critical">{error}</p>;
  }
  if (!workspace) {
    return <p className="text-xs text-muted-foreground">Reading your columns…</p>;
  }

  const onSave = async () => {
    setBusy(true);
    setError(null);
    try {
      await saveMapping(workspace.table, {
        upload_id: uploadId,
        // Decisions only. No sample values leave this component.
        decisions: workspace.source_columns.map((column) => ({
          header: column.header,
          decision: ignored[column.header] ? 'ignored'
            : chosen[column.header] ? 'mapped' : 'undecided',
          chosen: ignored[column.header] ? null : (chosen[column.header] ?? null),
          reason: ignored[column.header] ? 'Marked not needed by the operator.' : null,
        })),
        values,
        derive: {},
        confirmations,
      });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="border border-border rounded-xl p-6 space-y-4" data-testid="mapping-screen">
      <div className="flex items-baseline justify-between">
        <h3 className="text-sm font-bold">Match your columns to the {workspace.table} fields</h3>
        <button onClick={onCancel} className="text-xs text-muted-foreground hover:text-foreground">
          Back
        </button>
      </div>
      <p className="text-xs text-muted-foreground" data-testid="mapping-progress">
        {progress.label}. Your file has {workspace.row_count.toLocaleString()} rows.
        Sample values are shown to help you recognise a column; they are not stored.
      </p>

      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="text-xs text-muted-foreground">
              <th className="pb-2 pr-3 font-medium">Your column</th>
              <th className="pb-2 pr-3 font-medium">Why we suggested it</th>
              <th className="pb-2 pr-3 font-medium">Maps to</th>
              <th className="pb-2" />
            </tr>
          </thead>
          <tbody>
            {ordered.map((column) => (
              <ColumnRow
                key={column.header}
                column={column}
                chosen={chosen[column.header] ?? null}
                ignored={Boolean(ignored[column.header])}
                options={workspace.canonical_columns}
                onChoose={(c) => setChosen({ ...chosen, [column.header]: c })}
                onIgnore={(v) => setIgnored({ ...ignored, [column.header]: v })}
              />
            ))}
          </tbody>
        </table>
      </div>

      {/* Their vocabulary onto ours. Only for the gated columns, and only for
          words that are not already canonical - asking about a value that
          already says "Active" is the fastest way to make the tick
          meaningless. */}
      {workspace.source_columns.map((column) => {
        const canonical = ignored[column.header] ? null : chosen[column.header];
        if (!canonical || !gated.includes(canonical)) return null;
        const options = workspace.reject_enum_options[canonical] ?? [];
        const outstandingValues = valuesNeedingMapping(column, options);
        if (outstandingValues.length === 0) return null;
        return (
          <div key={`values-${column.header}`}
               className="border-t border-border pt-3 space-y-2"
               data-testid={`values-${canonical}`}>
            <p className="text-xs font-semibold">
              {outstandingValues.length} value
              {outstandingValues.length === 1 ? '' : 's'} in{' '}
              <span className="font-mono">{column.header}</span> need a meaning
            </p>
            {outstandingValues.map((value) => (
              <div key={value} className="flex items-center gap-2 text-xs">
                <span className="font-mono w-32 truncate">{value}</span>
                <ArrowRight className="w-3 h-3 text-muted-foreground shrink-0" />
                <select
                  value={values[canonical]?.[value] ?? ''}
                  data-testid={`value-${value}`}
                  onChange={(e) => {
                    const next = { ...(values[canonical] ?? {}) };
                    if (e.target.value) next[value] = e.target.value;
                    else delete next[value];
                    setValues({ ...values, [canonical]: next });
                    // A changed pair is a new assertion. Dropping the tick is
                    // the same rule the backend enforces at save and at load:
                    // an affirmation is keyed to the pair, never the column.
                    setConfirmations({ ...confirmations, [canonical]: {} });
                  }}
                  className="text-xs bg-transparent border border-border rounded px-2 py-1"
                >
                  <option value="">— choose —</option>
                  {options.map((o) => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
            ))}
          </div>
        );
      })}

      {gated.map((column) => {
        const pairs = values[column] ?? {};
        const entries = Object.entries(pairs);
        if (entries.length === 0) return null;
        const affirmed = confirmations[column] ?? {};
        const allAffirmed = entries.every(([k, v]) => affirmed[k] === v);
        return (
          <div key={column} className="border-t border-border pt-3 space-y-2"
               data-testid={`affirm-${column}`}>
            <p className="text-xs font-semibold">{column}</p>
            {workspace.reject_enum_consequences[column] && (
              <p className="text-xs text-warning">
                {workspace.reject_enum_consequences[column]}
              </p>
            )}
            <label className="flex items-start gap-2 text-xs">
              <input
                type="checkbox"
                checked={allAffirmed}
                onChange={(e) => setConfirmations({
                  ...confirmations,
                  [column]: e.target.checked ? { ...pairs } : {},
                })}
                className="mt-0.5"
              />
              <span>
                I confirm{' '}
                {entries.map(([from, to]) => `"${from}" means ${to}`).join(', ')}
                {' '}for this client.
              </span>
            </label>
          </div>
        );
      })}

      {focusHeader && (
        <p className="text-xs text-muted-foreground">
          Started from <span className="font-mono">{focusHeader}</span>.
        </p>
      )}
      {error && <p className="text-xs text-critical">{error}</p>}
      <div className="space-y-2">
        <button
          onClick={onSave}
          disabled={busy || blocked}
          data-testid="save-mapping"
          className="px-4 py-2 bg-primary text-primary-foreground text-xs font-semibold rounded-lg disabled:opacity-50 flex items-center gap-1.5"
        >
          {busy && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
          Save this mapping
        </button>
        {progress.needAttention > 0 && (
          <p className="text-xs text-critical">
            {progress.needAttention} column{progress.needAttention === 1 ? '' : 's'} still
            need a decision.
          </p>
        )}
        {unmeant && (
          <p className="text-xs text-critical">
            Some values still need a meaning.
          </p>
        )}
        {!unmeant && Object.keys(outstanding).length > 0 && (
          <p className="text-xs text-critical">
            Confirm the value meanings above before saving.
          </p>
        )}
      </div>
    </section>
  );
};
