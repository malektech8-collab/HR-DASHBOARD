import React, { useEffect, useState } from 'react';
import { Shield, ShieldAlert } from 'lucide-react';

interface GovernanceStatusData {
  current_gate: string;
  current_status: string;
  evidence_status: string;
  synthetic_validation_status: string;
  decision_recommendation: string;
  real_data_execution_approved: boolean;
  real_authorization_evidence_approved: boolean;
  load_scheduling_approved: boolean;
  go_no_go_meeting_held: boolean;
  stop_criteria_count: number;
  last_completed_milestone: string;
  milestone_3i_status: string;
  milestone_3j_status: string;
  milestone_3k_status: string;
}

export const GovernanceWidget: React.FC = () => {
  const [data, setData] = useState<GovernanceStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    fetch(`${API_BASE_URL}/api/governance/status`)
      .then((res) => {
        if (!res.ok) {
          throw new Error('Failed to fetch governance status');
        }
        return res.json();
      })
      .then((statusData: GovernanceStatusData) => {
        setData(statusData);
        setLoading(false);
      })
      .catch((err: any) => {
        console.error(err);
        setError(err.message || 'Error loading governance metadata');
        setLoading(false);
      });
  }, []);

  if (loading) {
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

  if (error || !data) {
    return (
      <div className="bg-destructive/5 border border-destructive/20 rounded-2xl p-6 text-foreground">
        <div className="flex items-center gap-2 text-destructive mb-2 font-semibold">
          <ShieldAlert className="w-5 h-5" />
          <span>Governance Load Failed</span>
        </div>
        <p className="text-xs text-muted-foreground">Unable to contact static governance API service.</p>
      </div>
    );
  }

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
        <span className="px-3 py-1 text-xs font-bold tracking-wider uppercase bg-amber-500/15 text-amber-400 border border-amber-500/30 rounded-full animate-pulse">
          {data.decision_recommendation}
        </span>
      </div>

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
