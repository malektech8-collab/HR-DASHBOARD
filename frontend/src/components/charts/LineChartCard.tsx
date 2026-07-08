import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export interface LineChartCardProps {
  title: string;
  xAxisData: string[];
  seriesData: number[];
  seriesName: string;
  color?: string; // Default: 'var(--primary)'
  valueFormatter?: (val: number) => string;
}

export const LineChartCard: React.FC<LineChartCardProps> = ({
  title,
  xAxisData,
  seriesData,
  seriesName,
  color = 'var(--primary)',
  valueFormatter = (val) => String(val)
}) => {
  const chartData = xAxisData.map((label, idx) => ({
    name: label,
    value: seriesData[idx]
  }));

  return (
    <div className="bg-card border border-border rounded-xl p-4 sm:p-5 shadow-lg flex flex-col h-[260px] sm:h-[300px] transition-theme">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">{title}</h3>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 8, right: 16, left: -24, bottom: 0 }}>
            <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
            <XAxis 
              dataKey="name" 
              stroke="var(--muted-foreground)" 
              fontSize={10}
              tickLine={false}
              axisLine={{ stroke: 'var(--border)' }}
            />
            <YAxis 
              stroke="var(--muted-foreground)" 
              fontSize={10}
              tickLine={false}
              axisLine={false}
              tickFormatter={valueFormatter}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'var(--card)', 
                borderColor: 'var(--border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--foreground)',
                fontFamily: 'var(--font-sans)',
                fontSize: '12px'
              }}
              labelClassName="text-muted-foreground text-[10px] font-semibold uppercase mb-1"
            />
            <Line 
              type="monotone" 
              dataKey="value" 
              name={seriesName}
              stroke={color}
              strokeWidth={3}
              dot={{ stroke: color, strokeWidth: 2, r: 4, fill: 'var(--card)' }}
              activeDot={{ r: 6, fill: color }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
