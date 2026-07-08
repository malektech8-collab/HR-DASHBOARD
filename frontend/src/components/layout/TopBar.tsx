import React from 'react';
import { Calendar, RefreshCw, Menu } from 'lucide-react';
import { formatDate } from '../../lib/formatters';
import { AppearanceMenu } from './AppearanceMenu';

interface TopBarProps {
  reportMonth: string;
  lastRefreshAt: string;
  refreshStatus: string;
  onRefreshTrigger?: () => void;
  onMenuClick: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  reportMonth,
  lastRefreshAt,
  refreshStatus,
  onRefreshTrigger,
  onMenuClick,
}) => {
  return (
    <header className="h-16 border-b border-border bg-card flex items-center justify-between px-4 sm:px-8 text-foreground fixed top-0 right-0 left-0 lg:left-64 z-10 transition-theme gap-3">
      {/* Mobile nav trigger */}
      <button
        type="button"
        onClick={onMenuClick}
        aria-label="Open navigation menu"
        className="lg:hidden p-2 -ml-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors shrink-0"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Page Context Details */}
      <div className="flex items-center gap-6 min-w-0">
        <div className="flex items-center gap-2 text-sm min-w-0">
          <Calendar className="w-4 h-4 text-primary shrink-0" />
          <span className="text-muted-foreground hidden sm:inline">Report Period:</span>
          <span className="font-semibold text-foreground bg-muted px-2 py-0.5 rounded border border-border whitespace-nowrap">
            {reportMonth || "2026-06"}
          </span>
        </div>
      </div>

      {/* Sync Status info */}
      <div className="flex items-center gap-2 sm:gap-4 shrink-0">
        <div className="text-right hidden md:block">
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

        <div className="hidden sm:flex items-center gap-1.5">
          <span className={`w-2.5 h-2.5 rounded-full ${
            refreshStatus === 'success' ? 'bg-healthy animate-pulse' : 'bg-critical'
          }`} />
          <span className="text-xs font-semibold capitalize text-muted-foreground">
            {refreshStatus === 'success' ? 'Online' : 'Sync Error'}
          </span>
        </div>

        <AppearanceMenu />
      </div>
    </header>
  );
};
