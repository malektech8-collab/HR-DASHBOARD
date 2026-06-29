import React from 'react';
import ReactECharts from 'echarts-for-react';

interface LineChartCardProps {
  title: string;
  xAxisData: string[];
  seriesData: number[];
  seriesName: string;
  color?: string;
  valueFormatter?: (val: number) => string;
}

export const LineChartCard: React.FC<LineChartCardProps> = ({
  title,
  xAxisData,
  seriesData,
  seriesName,
  color = '#38bdf8', // Sky 400
  valueFormatter = (val) => String(val)
}) => {
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#090d16',
      borderColor: '#1e293b',
      borderWidth: 1,
      textStyle: {
        color: '#f8fafc',
        fontSize: 12,
        fontFamily: 'Inter, sans-serif'
      },
      formatter: (params: any) => {
        const item = params[0];
        return `
          <div style="padding: 4px 8px;">
            <div style="color: #64748b; font-size: 10px; font-weight: 600; text-transform: uppercase; margin-bottom: 4px;">${item.name}</div>
            <div style="display: flex; items-center; gap: 8px;">
              <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: ${item.color}; margin-top: 5px;"></span>
              <span style="font-weight: 700;">${valueFormatter(item.value)}</span>
            </div>
          </div>
        `;
      }
    },
    grid: {
      top: '8%',
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: xAxisData,
      axisLine: {
        lineStyle: {
          color: '#1e293b'
        }
      },
      axisTick: {
        show: false
      },
      axisLabel: {
        color: '#64748b',
        fontSize: 11,
        fontFamily: 'Inter, sans-serif'
      }
    },
    yAxis: {
      type: 'value',
      splitLine: {
        lineStyle: {
          color: '#1e293b'
        }
      },
      axisLine: {
        show: false
      },
      axisLabel: {
        color: '#64748b',
        fontSize: 11,
        fontFamily: 'Inter, sans-serif'
      }
    },
    series: [
      {
        name: seriesName,
        data: seriesData,
        type: 'line',
        smooth: 0.3,
        showSymbol: true,
        symbol: 'circle',
        symbolSize: 8,
        itemStyle: {
          color: color
        },
        lineStyle: {
          width: 3,
          color: color
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: `${color}25` },
              { offset: 1, color: `${color}00` }
            ]
          }
        }
      }
    ]
  };

  return (
    <div className="bg-card border border-border rounded-xl p-5 shadow-lg flex flex-col h-[300px]">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">{title}</h3>
      <div className="flex-1 min-h-0">
        <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
      </div>
    </div>
  );
};
