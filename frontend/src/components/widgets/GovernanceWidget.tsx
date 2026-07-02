import React from 'react';
import { Shield, ShieldAlert, KeyRound, LogOut } from 'lucide-react';
import { useGovernanceStatus, useLoginMutation } from '../../hooks/useGovernance';

export const GovernanceWidget: React.FC = () => {
  const { data, isLoading, error, refetch } = useGovernanceStatus();
  const loginMutation = useLoginMutation();

  const handleMockLogin = async (roleKey: string) => {
    let username = '';
    let password = '';
    if (roleKey === 'admin') {
      username = 'admin@synthetic.local';
      password = 'adminpassword';
    } else if (roleKey === 'exec') {
      username = 'exec@synthetic.local';
      password = 'execpassword';
    } else if (roleKey === 'analyst') {
      username = 'hr@synthetic.local';
      password = 'hrpassword';
    }

    try {
      await loginMutation.mutateAsync({ username, password });
      refetch();
    } catch (err) {
      console.error('Login failed:', err);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    refetch();
  };

  if (isLoading) {
    return (
      <div className="bg-card/40 backdrop-blur-md border border-border p-6 rounded-2xl animate-pulse">
        <div className="h-5 bg-muted rounded w-1/3 mb-4"></div>
        <div className="space-y-2">
          <div className="h-4 bg-muted rounded w-3/4"></div>
          <div className="h-4 bg-muted rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  // Handle Unauthorized (401) or Forbidden (403) explicitly or general errors
  const isAuthError = error instanceof Error && (error.message.includes('401') || error.message.includes('403'));

  return (
    <div className="bg-gradient-to-br from-card/60 to-card/30 backdrop-blur-md border border-border p-6 rounded-2xl shadow-xl relative overflow-hidden">
      {/* Decorative background glow */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/5 rounded-full blur-3xl pointer-events-none"></div>

      {/* Widget Header */}
      <div className="flex items-center justify-between border-b border-border/60 pb-4 mb-4">
        <div className="flex items-center gap-2.5">
          <span className="p-1.5 bg-amber-500/10 text-amber-400 rounded-lg">
            <Shield className="w-5 h-5" />
          </span>
          <div>
            <h3 className="font-bold text-sm tracking-tight text-foreground">Governance Gate Status</h3>
            <p className="text-[10px] text-muted-foreground uppercase tracking-widest">GATE 5 CONTROL</p>
          </div>
        </div>
        {data && (
          <span className="px-3 py-1 text-xs font-bold tracking-wider uppercase bg-amber-500/15 text-amber-400 border border-amber-500/30 rounded-full animate-pulse">
            {data.decision_recommendation}
          </span>
        )}
      </div>

      {/* Role Selection / Auth Toolbar */}
      <div className="mb-5 p-3.5 bg-slate-950/60 border border-border/40 rounded-xl">
        <div className="flex items-center gap-2 text-xs font-semibold text-foreground mb-2.5">
          <KeyRound className="w-3.5 h-3.5 text-amber-400" />
          <span>Select Synthetic Identity (RBAC Session)</span>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => handleMockLogin('admin')}
            disabled={loginMutation.isPending}
            className="px-2.5 py-1 text-[11px] font-medium rounded-lg bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 border border-amber-500/20 transition-all cursor-pointer"
          >
            System Admin
          </button>
          <button
            onClick={() => handleMockLogin('exec')}
            disabled={loginMutation.isPending}
            className="px-2.5 py-1 text-[11px] font-medium rounded-lg bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 border border-indigo-500/20 transition-all cursor-pointer"
          >
            Executive
          </button>
          <button
            onClick={() => handleMockLogin('analyst')}
            disabled={loginMutation.isPending}
            className="px-2.5 py-1 text-[11px] font-medium rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 border border-emerald-500/20 transition-all cursor-pointer"
          >
            HR Analyst (403)
          </button>
          <button
            onClick={handleLogout}
            className="px-2.5 py-1 text-[11px] font-medium rounded-lg bg-muted text-muted-foreground hover:bg-muted/80 border border-border transition-all ml-auto flex items-center gap-1 cursor-pointer"
          >
            <LogOut className="w-3 h-3" />
            Clear Session
          </button>
        </div>
        {loginMutation.isPending && (
          <p className="text-[10px] text-muted-foreground mt-2 animate-pulse">Authenticating session token...</p>
        )}
      </div>

      {/* Auth-Specific UI Views */}
      {isAuthError || !data ? (
        <div className="bg-destructive/5 border border-destructive/20 rounded-2xl p-6 text-foreground mb-4">
          <div className="flex items-center gap-2 text-destructive mb-2 font-semibold">
            <ShieldAlert className="w-5 h-5" />
            <span>Access Denied (Fail Closed)</span>
          </div>
          <p className="text-xs text-muted-foreground">
            {error instanceof Error && error.message.includes('403')
              ? 'Your authenticated HR_ANALYST role does not possess permissions to view corporate governance states.'
              : 'Please select a valid synthetic identity above to generate a JWT token and establish session access.'}
          </p>
        </div>
      ) : (
        <>
          {/* Critical Status Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
            <div className="p-3 bg-slate-950/40 border border-border/50 rounded-xl">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Gate 5 Status</p>
              <p className="font-bold text-xs mt-1 text-amber-400">{data.current_status}</p>
            </div>

            <div className="p-3 bg-slate-950/40 border border-border/50 rounded-xl">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Evidence Status</p>
              <p className="font-bold text-xs mt-1 text-red-400">{data.evidence_status}</p>
            </div>

            <div className="p-3 bg-slate-950/40 border border-border/50 rounded-xl">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Validation State</p>
              <p className="font-bold text-xs mt-1 text-indigo-400">{data.synthetic_validation_status}</p>
            </div>

            <div className="p-3 bg-slate-950/40 border border-border/50 rounded-xl">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Stop Criteria Count</p>
              <p className="font-bold text-xs mt-1 text-foreground">{data.stop_criteria_count} Registered</p>
            </div>
          </div>

          {/* Authorization Checkboxes / Flags */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5 text-[11px] border-t border-border/40 pt-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
              <span>Real-data execution: <strong className="text-red-400">Not Approved</strong></span>
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
              <span>Load scheduling: <strong className="text-red-400">Not Approved</strong></span>
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-500"></span>
              <span>Go/No-Go meeting: <strong className="text-slate-400">Not Held</strong></span>
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              <span>Last Milestone: <strong className="text-emerald-400">{data.last_completed_milestone}</strong></span>
            </div>
          </div>
        </>
      )}

      {/* System Warning Banner */}
      <div className="bg-red-500/10 border border-red-500/20 p-3.5 rounded-xl flex items-start gap-2.5">
        <ShieldAlert className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
        <div>
          <p className="text-[11px] font-bold text-red-400 leading-tight">REAL-DATA EXECUTION LOCKED</p>
          <p className="text-[10px] text-muted-foreground mt-0.5 leading-relaxed">
            The project environment operates strictly on synthetic validation protocols. No live database connection is active, and production load scheduling is disabled.
          </p>
        </div>
      </div>
    </div>
  );
};
