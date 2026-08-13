import React, { useEffect, useState } from 'react';
import { CheckCircle2, Download, RefreshCw, Trash2, UploadCloud } from 'lucide-react';

import { OnboardingStatusTable } from '../components/widgets/OnboardingStatusTable';
import { ViolationPanels } from '../components/widgets/ViolationPanels';
import { fetchTemplates, getTemplateDownloadUrl } from '../lib/api';
import { ApiError, getToken, login } from '../lib/http';
import { commitGate } from '../lib/uploadFlow';
import { MappingPanel } from '../components/widgets/MappingPanel';
import { MappingScreen } from '../components/widgets/MappingScreen';
import {
  commitUpload,
  discardUpload,
  fetchOnboardingStatus,
  previewUpload,
  stageUpload,
} from '../lib/uploads';
import type {
  CommitDeclaration,
  OnboardingStatus,
  RefreshReport,
  UploadPreview,
} from '../lib/uploads';
import type { TemplateInfo } from '../lib/api';

/**
 * Data Onboarding: pick a domain, download the template, upload, see what is
 * wrong, declare coverage, commit.
 *
 * The loop this page is built around is upload -> errors -> fix -> upload, not
 * the happy path. A first real upload will fail, probably several times, so
 * the errors stay on screen while a corrected file is chosen.
 *
 * Login is SCOPED to this page by ruling: the endpoints behind it are the only
 * authenticated ones, and an app-wide login is a product decision (sessions,
 * roles, recovery, SSO) that belongs with Phase 3 hardening rather than being a
 * side effect of an upload screen.
 */

// `map` sits between upload and review because that is where it happens:
// the preview is what discovers the profile is incomplete, and the review
// step is where the client is sent back from.
type Step = 'pick' | 'upload' | 'map' | 'review' | 'done';

export const ScopedLogin: React.FC<{ onDone: () => void }> = ({ onDone }) => {
  const [username, setUsername] = useState('admin@synthetic.local');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username, password);
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-in failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <form
      onSubmit={submit}
      data-testid="scoped-login"
      className="max-w-sm mx-auto my-16 border border-border rounded-xl p-6 space-y-4"
    >
      <div>
        <h3 className="text-lg font-bold">Sign in to upload data</h3>
        <p className="text-xs text-muted-foreground mt-1">
          Uploading changes what the dashboard reports, so it needs an
          authenticated operator. The rest of the dashboard is unaffected.
        </p>
      </div>
      <input
        className="w-full px-3 py-2 text-sm bg-muted border border-border rounded-lg"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        placeholder="Email"
        autoComplete="username"
      />
      <input
        className="w-full px-3 py-2 text-sm bg-muted border border-border rounded-lg"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
        autoComplete="current-password"
      />
      {error && <p className="text-xs text-critical">{error}</p>}
      <button
        type="submit"
        disabled={busy}
        className="w-full px-4 py-2 bg-primary text-primary-foreground text-sm font-semibold rounded-lg disabled:opacity-50"
      >
        {busy ? 'Signing in…' : 'Sign in'}
      </button>
    </form>
  );
};

export const DataOnboarding: React.FC = () => {
  const [authed, setAuthed] = useState(() => Boolean(getToken()));
  const [tab, setTab] = useState<'status' | 'upload'>('status');

  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [table, setTable] = useState<string | null>(null);
  const [step, setStep] = useState<Step>('pick');

  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<UploadPreview | null>(null);
  const [declaration, setDeclaration] = useState<CommitDeclaration>({});
  const [confirmed, setConfirmed] = useState(false);
  const [focusHeader, setFocusHeader] = useState<string | undefined>();
  const [report, setReport] = useState<RefreshReport | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshStatus = React.useCallback(async () => {
    try {
      setStatus(await fetchOnboardingStatus());
    } catch (err) {
      if (err instanceof ApiError && err.isUnauthorized) setAuthed(false);
      else setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    if (!authed) return;
    refreshStatus();
    fetchTemplates().then(setTemplates).catch(() => setTemplates([]));
  }, [authed, refreshStatus]);

  if (!authed) {
    return <ScopedLogin onDone={() => setAuthed(true)} />;
  }

  const run = async (label: string, action: () => Promise<void>) => {
    setBusy(label);
    setError(null);
    try {
      await action();
    } catch (err) {
      if (err instanceof ApiError && err.isUnauthorized) setAuthed(false);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  };

  const onStage = () => run('staging', async () => {
    if (!table || !file) return;
    const staged = await stageUpload(table, file);
    const result = await previewUpload(staged.upload_id);
    setPreview(result);
    setDeclaration({
      coverage_start: result.suggested_coverage_start,
      coverage_end: result.suggested_coverage_end,
      history_since: null,
    });
    setConfirmed(false);
    setStep('review');
  });

  const onDiscard = () => run('discarding', async () => {
    if (preview) await discardUpload(preview.upload.upload_id);
    setPreview(null);
    setFile(null);
    setStep('upload');
  });

  const onCommit = () => run('committing', async () => {
    if (!preview) return;
    setReport(await commitUpload(preview.upload.upload_id, declaration));
    setStep('done');
    await refreshStatus();
  });

  // Both rules live in lib/uploadFlow.ts and are tested as a truth table.
  // They either block a valid commit or admit bad data, so they are not
  // something to verify by driving this DOM.
  const gate = commitGate(preview, { declaration, confirmed }, busy !== null);

  return (
    <div className="space-y-6 animate-fadeIn">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Data Onboarding</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Upload your data one domain at a time. Nothing is committed until
            you have seen what it contains.
          </p>
        </div>
        <div className="flex gap-1 text-xs">
          {(['status', 'upload'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1.5 rounded-lg font-semibold ${
                tab === t ? 'bg-primary text-primary-foreground'
                          : 'bg-muted text-muted-foreground hover:text-foreground'
              }`}
            >
              {t === 'status' ? 'Progress' : 'Upload'}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="border border-critical/30 bg-critical/5 text-critical text-xs rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      {tab === 'status' && status && (
        <OnboardingStatusTable
          status={status}
          onUpload={(domain) => { setTable(domain); setTab('upload'); setStep('upload'); }}
        />
      )}

      {tab === 'upload' && (
        <div className="space-y-6">
          {/* 1. pick a domain — the picker IS the contracted-domain list, so
                 an uncontracted domain cannot be chosen */}
          <section className="border border-border rounded-xl p-6 space-y-4">
            <h3 className="text-sm font-bold">1. Choose what you are uploading</h3>
            <div className="flex flex-wrap gap-2">
              {templates.map((t) => (
                <button
                  key={t.name}
                  onClick={() => { setTable(t.name); setStep('upload'); setPreview(null); }}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg border ${
                    table === t.name
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'bg-muted text-muted-foreground border-border hover:text-foreground'
                  }`}
                >
                  {t.label || t.name}
                </button>
              ))}
            </div>
            {/* A limitation the client can be harmed by not knowing has to be
                read BEFORE the upload, beside the template they are about to
                fill in - not discovered afterwards in a board pack. */}
            {table && templates.find((t) => t.name === table)?.instructions && (
              <p
                className="text-xs text-warning border border-warning/30 bg-warning/5 rounded-lg p-3"
                data-testid="template-instructions"
              >
                {templates.find((t) => t.name === table)?.instructions}
              </p>
            )}
            {table && (
              <a
                href={getTemplateDownloadUrl(table)}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline"
              >
                <Download className="w-3.5 h-3.5" /> Download the {table} template
              </a>
            )}
          </section>

          {/* 2. upload */}
          {table && step !== 'done' && (
            <section className="border border-border rounded-xl p-6 space-y-4">
              <h3 className="text-sm font-bold">2. Upload your file</h3>
              <p className="text-xs text-muted-foreground">
                CSV only. The file is checked against the {table} contract
                before anything is committed — the filename does not matter.
              </p>
              <input
                type="file"
                accept=".csv"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="block w-full text-xs"
              />
              <button
                onClick={onStage}
                disabled={!file || busy !== null}
                className="px-4 py-2 bg-primary text-primary-foreground text-xs font-semibold rounded-lg disabled:opacity-50 flex items-center gap-1.5"
              >
                {busy === 'staging' && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <UploadCloud className="w-3.5 h-3.5" /> Check this file
              </button>
            </section>
          )}

          {/* 2b. map — only when the profile is incomplete. A client whose
                 export already matches never sees this. */}
          {preview && step === 'map' && (
            <MappingScreen
              uploadId={preview.upload.upload_id}
              focusHeader={focusHeader}
              onCancel={() => { setFocusHeader(undefined); setStep('review'); }}
              onSaved={async () => {
                // Re-preview rather than patching state: the mapping is applied
                // server-side, and the client should never hold its own idea of
                // what a profile did.
                setFocusHeader(undefined);
                setBusy('previewing');
                try {
                  setPreview(await previewUpload(preview.upload.upload_id));
                  setStep('review');
                } catch (err) {
                  setError(err instanceof Error ? err.message : String(err));
                } finally {
                  setBusy(null);
                }
              }}
            />
          )}

          {/* 3. review — validation results and preview are one screen,
                 because they are one request */}
          {preview && step === 'review' && (
            <section className="border border-border rounded-xl p-6 space-y-5">
              <div className="flex items-baseline justify-between">
                <h3 className="text-sm font-bold">3. What we found</h3>
                <button
                  onClick={onDiscard}
                  className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
                >
                  <Trash2 className="w-3.5 h-3.5" /> Discard
                </button>
              </div>

              <dl className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                <div><dt className="text-muted-foreground">Rows</dt>
                  <dd className="font-bold">{preview.row_count.toLocaleString()}</dd></div>
                <div><dt className="text-muted-foreground">Columns</dt>
                  <dd className="font-bold">{preview.columns_present.length}</dd></div>
                <div><dt className="text-muted-foreground">Missing</dt>
                  <dd className="font-bold">{preview.columns_missing.length}</dd></div>
                <div><dt className="text-muted-foreground">Unexpected</dt>
                  <dd className="font-bold">{preview.columns_unexpected.length}</dd></div>
              </dl>

              <MappingPanel
                mapping={preview.mapping}
                onFix={(header) => { setFocusHeader(header); setStep('map'); }}
              />

              <ViolationPanels preview={preview} />

              {/* 4. declare — suggested by the preview, confirmed by the human */}
              {(preview.coverage_required || preview.history_required) && (
                <div className="border-t border-border pt-4 space-y-3">
                  <h4 className="text-xs font-bold uppercase text-muted-foreground">
                    4. Confirm what this file covers
                  </h4>
                  {preview.coverage_required && (
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <span className="text-muted-foreground">Covers</span>
                      <input
                        type="date"
                        value={declaration.coverage_start ?? ''}
                        onChange={(e) => { setDeclaration({ ...declaration, coverage_start: e.target.value }); setConfirmed(false); }}
                        className="px-2 py-1 bg-muted border border-border rounded"
                      />
                      <span className="text-muted-foreground">to</span>
                      <input
                        type="date"
                        value={declaration.coverage_end ?? ''}
                        onChange={(e) => { setDeclaration({ ...declaration, coverage_end: e.target.value }); setConfirmed(false); }}
                        className="px-2 py-1 bg-muted border border-border rounded"
                      />
                      <span className="text-muted-foreground">
                        Working days outside this range are reported as unknown,
                        not as absences.
                      </span>
                    </div>
                  )}
                  {preview.history_required && (
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <span className="text-muted-foreground">History reaches back to</span>
                      <input
                        type="date"
                        value={declaration.history_since ?? ''}
                        onChange={(e) => { setDeclaration({ ...declaration, history_since: e.target.value }); setConfirmed(false); }}
                        className="px-2 py-1 bg-muted border border-border rounded"
                      />
                      <span className="text-muted-foreground">
                        Months before this show as unavailable rather than estimated.
                      </span>
                    </div>
                  )}
                  <label className="flex items-start gap-2 text-xs">
                    <input
                      type="checkbox"
                      checked={confirmed}
                      onChange={(e) => setConfirmed(e.target.checked)}
                      className="mt-0.5"
                    />
                    <span>I confirm this is what the file covers.</span>
                  </label>
                </div>
              )}

              {/* 5. commit */}
              <div className="border-t border-border pt-4 space-y-2">
                <button
                  onClick={onCommit}
                  disabled={!gate.enabled}
                  data-testid="commit-button"
                  className="px-4 py-2 bg-primary text-primary-foreground text-xs font-semibold rounded-lg disabled:opacity-50 flex items-center gap-1.5"
                >
                  {busy === 'committing' && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  {gate.label}
                </button>
                {gate.blockedBecause && (
                  <p className={`text-xs ${gate.blockKind === 'declaration' ? 'text-muted-foreground' : 'text-critical'}`}>
                    {gate.blockedBecause}
                    {(gate.blockKind === 'unmapped-columns'
                      || gate.blockKind === 'unmapped-values') && (
                      <button
                        onClick={() => setStep('map')}
                        className="ml-1 underline font-semibold"
                        data-testid="goto-mapping"
                      >
                        Fix the mapping
                      </button>
                    )}
                  </p>
                )}
                {busy === 'committing' && (
                  <p className="text-xs text-muted-foreground">
                    Validating, ingesting and rebuilding the warehouse. This
                    takes a few minutes on a full dataset.
                  </p>
                )}
              </div>
            </section>
          )}

          {step === 'done' && report && (
            <section className="border border-healthy/30 bg-healthy/5 rounded-xl p-6 space-y-3">
              <h3 className="text-sm font-bold text-healthy flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" /> Committed
              </h3>
              <p className="text-xs text-muted-foreground">
                The pipeline finished in {report.execution_time_seconds}s. The
                dashboard now reflects this upload.
              </p>
              <button
                onClick={() => { setStep('pick'); setPreview(null); setFile(null); setReport(null); setTab('status'); }}
                className="px-4 py-2 bg-primary text-primary-foreground text-xs font-semibold rounded-lg"
              >
                Upload another domain
              </button>
            </section>
          )}
        </div>
      )}
    </div>
  );
};
