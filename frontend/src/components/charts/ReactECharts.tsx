import React from 'react';
import { 
  ResponsiveContainer, 
  LineChart, Line, 
  BarChart, Bar, 
  PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend 
} from 'recharts';

interface ReactEChartsProps {
  option: any;
  style?: React.CSSProperties;
}

export const ReactECharts: React.FC<ReactEChartsProps> = ({ option, style }) => {
  if (!option) return null;

  // Determine type of chart from the series
  const series = option.series || [];
  const primarySeries = series[0] || {};
  const chartType = primarySeries.type || 'line';

  // 1. Parse xAxis Data
  const xAxisData = option.xAxis?.data || [];

  // 2. Format Data for Recharts
  let chartData: any[] = [];
  
  if (chartType === 'pie' || chartType === 'funnel') {
    chartData = primarySeries.data || [];
  } else {
    if (xAxisData.length > 0) {
      chartData = xAxisData.map((label: string, idx: number) => {
        const item: any = { name: label };
        series.forEach((s: any) => {
          if (s.data && s.data[idx] !== undefined) {
            const val = s.data[idx];
            item[s.name || 'value'] = typeof val === 'object' && val !== null ? val.value : val;
          }
        });
        return item;
      });
    }
  }

  // 3. Define height
  const height = style?.height || 300;

  // 4. Render Recharts components
  if (chartType === 'pie' || chartType === 'funnel') {
    const COLORS = [
      'var(--primary)',
      'var(--accent)',
      'var(--healthy)',
      'var(--warning)',
      'var(--critical)',
      '#a855f7',
      '#ec4899',
      '#f43f5e'
    ];

    return (
      <div style={{ width: '100%', height }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip
              contentStyle={{
                backgroundColor: 'var(--card)',
                borderColor: 'var(--border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--foreground)',
                fontFamily: 'var(--font-sans)',
                fontSize: '12px'
              }}
            />
            <Legend 
              verticalAlign="bottom" 
              height={36} 
              iconType="circle"
              wrapperStyle={{ fontSize: '11px', fontFamily: 'var(--font-sans)' }}
            />
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={chartType === 'funnel' ? 0 : 50}
              outerRadius={80}
              paddingAngle={3}
              dataKey="value"
              nameKey="name"
            >
              {chartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
    );
  }

  const renderSeries = () => {
    return series.map((s: any, idx: number) => {
      const colorOptions = [
        'var(--primary)',
        'var(--accent)',
        'var(--healthy)',
        'var(--warning)',
        'var(--critical)'
      ];
      let strokeColor = colorOptions[idx % colorOptions.length];
      if (s.itemStyle?.color) {
        const itemColor = String(s.itemStyle.color).toLowerCase();
        if (itemColor.startsWith('#')) {
          if (itemColor === '#38bdf8') strokeColor = 'var(--primary)';
          else if (itemColor === '#6366f1') strokeColor = 'var(--accent)';
          else if (itemColor === '#10b981') strokeColor = 'var(--healthy)';
          else if (itemColor === '#f59e0b') strokeColor = 'var(--warning)';
          else if (itemColor === '#ef4444') strokeColor = 'var(--critical)';
        }
      }

      if (chartType === 'bar' || s.type === 'bar') {
        return (
          <Bar 
            key={s.name || idx} 
            dataKey={s.name || 'value'} 
            fill={strokeColor} 
            radius={[4, 4, 0, 0]}
            maxBarSize={40}
          />
        );
      } else {
        return (
          <Line
            key={s.name || idx}
            type="monotone"
            dataKey={s.name || 'value'}
            stroke={strokeColor}
            strokeWidth={3}
            dot={{ stroke: strokeColor, strokeWidth: 2, r: 4, fill: 'var(--card)' }}
            activeDot={{ r: 6, fill: strokeColor }}
          />
        );
      }
    });
  };

  const hasLegend = option.legend?.data && option.legend.data.length > 0;

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        {chartType === 'bar' ? (
          <BarChart data={chartData} margin={{ top: 8, right: 16, left: -24, bottom: hasLegend ? 16 : 0 }}>
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
            {hasLegend && (
              <Legend 
                verticalAlign="bottom" 
                height={36} 
                iconType="circle"
                wrapperStyle={{ fontSize: '11px', fontFamily: 'var(--font-sans)' }}
              />
            )}
            {renderSeries()}
          </BarChart>
        ) : (
          <LineChart data={chartData} margin={{ top: 8, right: 16, left: -24, bottom: hasLegend ? 16 : 0 }}>
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
            {hasLegend && (
              <Legend 
                verticalAlign="bottom" 
                height={36} 
                iconType="circle"
                wrapperStyle={{ fontSize: '11px', fontFamily: 'var(--font-sans)' }}
              />
            )}
            {renderSeries()}
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  );
};

export default ReactECharts;
