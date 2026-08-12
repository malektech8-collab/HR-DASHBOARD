import React, { useState } from 'react';
import { AlertTriangle, Download, XCircle } from 'lucide-react';

import {
  buildErrorReport,
  errorReportFilename,
  groupByColumn,
} from '../../lib/uploads';
import type { UploadPreview, Violation } from '../../lib/uploads';

/**
 * REJECT and EXCEPTION, in two separate regions — never one list sorted by
 * severity.
 *
 * They are not two points on a scale. They differ in WHAT HAPPENS NEXT:
 *
 *   REJECT     the file is wrong; commit is blocked; the export owner fixes it
 *   EXCEPTION  the data has a problem the business already has; it loads, and
 *              appears on the Data Quality page; HR fixes it over time
 *
 * Sorting them together would imply a spectrum and lose that.
 *
 * The default view groups by COLUMN because that is the shape of the fix: a
 * user opens one column in their spreadsheet and corrects it. It also collapses
 * the commonest real case — one bad export column producing hundreds of
 * violations — into a single line.
 */

function download(filename: string, body: string) {
  const blob = new Blob([body], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

const ByColumn: React.FC<{ violations: Violation[] }> = ({ violations }) => (
  <ul className="space-y-2">
    {groupByColumn(violations).map((group) => (
      <li key={group.column} className="text-xs">
        <div className="flex items-baseline justify-between gap-3">
          <span className="font-semibold">{group.column}</span>
          <span className="text-muted-foreground shrink-0">
            {group.count} {group.count === 1 ? 'row' : 'rows'} · {group.rule}
          </span>
        </div>
        <p className="text-muted-foreground mt-0.5">{group.example.message_en}</p>
        <p className="text-muted-foreground" dir="rtl">{group.example.message_ar}</p>
        {group.rows.length > 0 && (
          <p className="text-[11px] text-muted-foreground mt-0.5">
            rows {group.rows.slice(0, 8).join(', ')}
            {group.rows.length > 8 ? ` … (+${group.rows.length - 8})` : ''}
          </p>
        )}
      </li>
    ))}
  </ul>
);

const ByRow: React.FC<{ violations: Violation[] }> = ({ violations }) => (
  <ul className="space-y-1.5">
    {violations.map((v, i) => (
      <li key={i} className="text-xs">
        <span className="font-semibold">
          {v.row !== null ? `Row ${v.row}` : 'File'}
          {v.column ? ` · ${v.column}` : ''}
        </span>
        <p className="text-muted-foreground">{v.message_en}</p>
      </li>
    ))}
  </ul>
);

interface Props {
  preview: UploadPreview;
}

export const ViolationPanels: React.FC<Props> = ({ preview }) => {
  const [view, setView] = useState<'column' | 'row'>('column');
  const hasAny = preview.rejects.length > 0 || preview.exceptions.length > 0;

  if (!hasAny) {
    return (
      <div className="border border-healthy/30 bg-healthy/5 rounded-lg p-4 text-xs">
        <span className="font-semibold text-healthy">No violations.</span>{' '}
        {preview.row_count.toLocaleString()} rows checked against the contract.
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="violation-panels">
      <div className="flex items-center justify-between gap-3">
        <div className="flex gap-1 text-xs">
          {(['column', 'row'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setView(mode)}
              className={`px-2.5 py-1 rounded-md font-semibold ${
                view === mode
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:text-foreground'
              }`}
            >
              by {mode}
            </button>
          ))}
        </div>
        {/* The fix happens in Excel, not in a browser tab. */}
        <button
          onClick={() => download(errorReportFilename(preview),
                                  buildErrorReport(preview))}
          className="px-3 py-1.5 border border-border text-xs font-semibold rounded-lg hover:bg-muted flex items-center gap-1.5"
        >
          <Download className="w-3.5 h-3.5" /> Download error report
        </button>
      </div>

      {preview.rejects.length > 0 && (
        <section
          data-testid="reject-panel"
          className="border border-critical/30 bg-critical/5 rounded-lg p-4 space-y-3"
        >
          <header className="flex items-center gap-2">
            <XCircle className="w-4 h-4 text-critical" />
            <h4 className="text-sm font-bold text-critical">
              {preview.rejects.length} must be fixed before this can be committed
            </h4>
          </header>
          <p className="text-xs text-muted-foreground">
            The file does not match the contract. Fix these and re-upload —
            nothing has been committed.
          </p>
          {view === 'column'
            ? <ByColumn violations={preview.rejects} />
            : <ByRow violations={preview.rejects} />}
        </section>
      )}

      {preview.exceptions.length > 0 && (
        <section
          data-testid="exception-panel"
          className="border border-warning/30 bg-warning/5 rounded-lg p-4 space-y-3"
        >
          <header className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-warning" />
            <h4 className="text-sm font-bold text-warning">
              {preview.exceptions.length} data-quality {preview.exceptions.length === 1
                ? 'exception' : 'exceptions'}
            </h4>
          </header>
          <p className="text-xs text-muted-foreground">
            These do not block the upload. The file will load and they will
            appear on the Data Quality page for HR to work through.
          </p>
          {view === 'column'
            ? <ByColumn violations={preview.exceptions} />
            : <ByRow violations={preview.exceptions} />}
        </section>
      )}
    </div>
  );
};
