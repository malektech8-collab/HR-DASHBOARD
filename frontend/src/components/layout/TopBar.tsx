import React from 'react';
import { Calendar, RefreshCw } from 'lucide-react';
import { formatDate } from '../../lib/formatters';

interface TopBarProps {
  reportMonth: string;
  lastRefreshAt: string;
  refreshStatus: string;
  onRefreshTrigger?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({ 
  reportMonth, 
  lastRefreshAt, 
  refreshStatus,
  onRefreshTrigger
}) => {
  return (
    <header className="h-16 border-b border-border bg-card flex items-center justify-between px-8 text-foreground fixed top-0 right-0 left-64 z-10">
      {/* Page Context Details */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 text-sm">
          <Calendar className="w-4 h-4 text-primary" />
          <span className="text-muted-foreground">Report Period:</span>
          <span className="font-semibold text-foreground bg-muted px-2 py-0.5 rounded border border-border">
            {reportMonth || "2026-06"}
          </span>
        </div>
      </div>

      {/* Sync Status info */}
      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-[11px] text-muted-foreground">Warehouse Sync Status</p>
          <p className="text-xs font-medium text-foreground">
            Last sync: <span className="text-muted-foreground">{formatDate(lastRefreshAt)}</span>
          </p>
        </div>

        {onRefreshTrigger && (
          <button
            onClick={onRefreshTrigger}
            disabled={refreshStatus === 'refreshing'}
            className="p-2 rounded-lg border border-border hover:bg-muted text-muted-foreground hover:text-foreground transition-all disabled:opacity-50"
            title="Trigger pipeline data rebuild"
          >
            <RefreshCw className={`w-4 h-4 ${refreshStatus === 'refreshing' ? 'animate-spin text-primary' : ''}`} />
          </button>
        )}

        <div className="flex items-center gap-1.5">
          <span className={`w-2.5 h-2.5 rounded-full ${
            refreshStatus === 'success' ? 'bg-healthy animate-pulse' : 'bg-critical'
          }`} />
          <span className="text-xs font-semibold capitalize text-muted-foreground">
            {refreshStatus === 'success' ? 'Online' : 'Sync Error'}
          </span>
        </div>
      </div>
    </header>
  );
};
