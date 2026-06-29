import React from 'react';
import { ArrowUpRight, ArrowDownRight, Minus, AlertTriangle } from 'lucide-react';
import { formatNumber, formatCurrency, formatPercent } from '../../lib/formatters';

interface KpiCardProps {
  label: string;
  value: number;
  unit: string;
  trendValue?: number;
  trendDirection?: 'up' | 'down' | 'flat';
  status: 'healthy' | 'warning' | 'critical' | 'neutral';
}

export const KpiCard: React.FC<KpiCardProps> = ({
  label,
  value,
  unit,
  trendValue,
  trendDirection,
  status
}) => {
  // Format the primary display value depending on the unit type
  let displayValue = '';
  if (unit === 'SAR') {
    displayValue = formatCurrency(value);
  } else if (unit === '%') {
    displayValue = formatPercent(value);
  } else {
    displayValue = formatNumber(value);
  }

  // Define semantic borders and glowing rings based on status
  const statusConfig = {
    healthy: {
      border: 'border-healthy/30 focus-within:border-healthy',
      glow: 'shadow-healthy/5',
      text: 'text-healthy',
      bg: 'bg-healthy/5'
    },
    warning: {
      border: 'border-warning/30 focus-within:border-warning',
      glow: 'shadow-warning/5',
      text: 'text-warning',
      bg: 'bg-warning/5'
    },
    critical: {
      border: 'border-critical/30 focus-within:border-critical',
      glow: 'shadow-critical/5',
      text: 'text-critical',
      bg: 'bg-critical/5'
    },
    neutral: {
      border: 'border-border focus-within:border-primary',
      glow: 'shadow-none',
      text: 'text-muted-foreground',
      bg: 'bg-muted/10'
    }
  };

  const currentStatus = statusConfig[status] || statusConfig.neutral;

  return (
    <div className={`bg-card border ${currentStatus.border} rounded-xl p-5 shadow-lg ${currentStatus.glow} transition-all duration-300 hover:translate-y-[-2px] flex flex-col justify-between min-h-[140px]`}>
      {/* Top Header Row */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</span>
        {status === 'critical' && <AlertTriangle className="w-4 h-4 text-critical animate-bounce" />}
      </div>

      {/* Main Metric Value Row */}
      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-2xl font-bold tracking-tight text-foreground">{displayValue}</span>
        <span className="text-xs text-muted-foreground">{unit.toLowerCase() !== 'sar' && unit.toLowerCase() !== '%' ? unit : ''}</span>
      </div>

      {/* Footer Trend Indicator Row */}
      <div className="mt-3 pt-2 border-t border-border/50 flex items-center justify-between text-xs">
        {trendValue !== undefined && trendDirection ? (
          <div className="flex items-center gap-1">
            <span className={`flex items-center font-semibold ${
              trendDirection === 'up' 
                ? 'text-healthy' 
                : trendDirection === 'down' 
                  ? 'text-critical' 
                  : 'text-muted-foreground'
            }`}>
              {trendDirection === 'up' && <ArrowUpRight className="w-3.5 h-3.5" />}
              {trendDirection === 'down' && <ArrowDownRight className="w-3.5 h-3.5" />}
              {trendDirection === 'flat' && <Minus className="w-3.5 h-3.5" />}
              {Math.abs(trendValue)}%
            </span>
            <span className="text-muted-foreground text-[10px]">vs last month</span>
          </div>
        ) : (
          <span className="text-muted-foreground text-[10px]">No historical data</span>
        )}

        {/* Small Status Badge */}
        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${currentStatus.bg} ${currentStatus.text}`}>
          {status}
        </span>
      </div>
    </div>
  );
};
