import React, { useState } from 'react';
import { Lock, RefreshCw } from 'lucide-react';

import { ApiError, clearToken, getToken, login } from '../../lib/http';

/**
 * The application's login gate.
 *
 * WHY IT EXISTS NOW AND NOT BEFORE. Measured before this cycle: 83 API routes,
 * and `get_current_user` on six of them. Every page fetched without a token and
 * got a 200 — including `/api/workforce/exceptions`, which returned employee
 * names to an anonymous caller. The frontend "worked" because the backend was
 * open.
 *
 * So this is not a new feature so much as the visible half of closing that. A
 * read path that worked only because it was unauthenticated was exposed, not
 * working.
 *
 * DataOnboarding shipped its own scoped login in the upload cycle, for exactly
 * this reason at a smaller scale. This replaces the need for it: once the whole
 * app is behind a gate, a page-level login is a second door into the same room.
 */

export const LoginGate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [authed, setAuthed] = useState(() => Boolean(getToken()));
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (authed) {
    return (
      <>
        {children}
        <button
          onClick={() => { clearToken(); setAuthed(false); }}
          className="fixed bottom-3 right-3 text-xs text-muted-foreground hover:text-foreground underline"
          data-testid="sign-out"
        >
          Sign out
        </button>
      </>
    );
  }

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      setAuthed(true);
    } catch (err) {
      // One message for every failure. The backend deliberately does not say
      // whether the account exists, and neither should this.
      setError(err instanceof ApiError && err.status === 503
        ? 'This deployment has not been set up yet. Ask your administrator to create the first account.'
        : 'Incorrect email or password.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-6">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm border border-border rounded-xl p-6 space-y-4"
        data-testid="login-gate"
      >
        <header className="flex items-center gap-2">
          <Lock className="w-4 h-4 text-primary" />
          <h1 className="text-sm font-bold">HR Analytics — sign in</h1>
        </header>
        <p className="text-xs text-muted-foreground">
          This dashboard shows employee records, salaries and government
          compliance status. It requires an account.
        </p>
        <label className="block space-y-1">
          <span className="text-xs text-muted-foreground">Email</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
            required
            className="w-full text-xs bg-transparent border border-border rounded px-2 py-1.5"
          />
        </label>
        <label className="block space-y-1">
          <span className="text-xs text-muted-foreground">Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
            className="w-full text-xs bg-transparent border border-border rounded px-2 py-1.5"
          />
        </label>
        {error && <p className="text-xs text-critical" data-testid="login-error">{error}</p>}
        <button
          type="submit"
          disabled={busy}
          className="w-full px-4 py-2 bg-primary text-primary-foreground text-xs font-semibold rounded-lg disabled:opacity-50 flex items-center justify-center gap-1.5"
        >
          {busy && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
          Sign in
        </button>
      </form>
    </div>
  );
};
