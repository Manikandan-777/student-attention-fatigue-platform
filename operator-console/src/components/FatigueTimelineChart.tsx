import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { TOKENS } from '../tokens';

export interface FatigueDataPoint {
  time: string;
  fatiguedCount: number;
}

interface FatigueTimelineChartProps {
  data: FatigueDataPoint[];
}

export const FatigueTimelineChart: React.FC<FatigueTimelineChartProps> = ({ data }) => {
  const latestCount = data.length > 0 ? data[data.length - 1].fatiguedCount : 0;

  return (
    <div className="bg-bg-surface border border-border-subtle rounded-radius-xl p-space-6 shadow-sm space-y-space-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-bold text-text-primary">
            Fatigue Timeline
          </h3>
          <p className="text-xs text-text-secondary">
            Count of students exhibiting fatigue indicators over time
          </p>
        </div>
        <div className="text-right">
          <span className="text-xs text-text-muted">Current</span>
          <div className="text-lg font-bold text-accent-danger">
            {latestCount}
          </div>
        </div>
      </div>

      <div className="h-64 w-full">
        {data.length === 0 ? (
          <div className="h-full flex items-center justify-center text-sm text-text-muted">
            Waiting for telemetry samples...
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke={TOKENS.colors['border-subtle']} />
              <XAxis
                dataKey="time"
                stroke={TOKENS.colors['text-muted']}
                tick={{ fontSize: 11 }}
              />
              <YAxis
                allowDecimals={false}
                stroke={TOKENS.colors['text-muted']}
                tick={{ fontSize: 11 }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: TOKENS.colors['bg-surface'],
                  borderColor: TOKENS.colors['border-subtle'],
                  borderRadius: TOKENS.radius.md,
                }}
              />
              <Area
                type="monotone"
                dataKey="fatiguedCount"
                name="Fatigued Students"
                stroke={TOKENS.colors['accent-danger']}
                fill={TOKENS.colors['accent-danger']}
                fillOpacity={0.15}
                strokeWidth={2}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Screen reader text alternative */}
      <details className="text-xs text-text-muted pt-space-2">
        <summary className="cursor-pointer font-medium hover:text-text-body">
          Accessible data view (tabular)
        </summary>
        <div className="max-h-32 overflow-y-auto mt-space-2 border border-border-subtle rounded-radius-md p-space-2">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-border-subtle">
                <th className="py-space-1">Time</th>
                <th className="py-space-1">Fatigued Count</th>
              </tr>
            </thead>
            <tbody>
              {data.slice(-10).map((pt, i) => (
                <tr key={i} className="border-b border-border-subtle">
                  <td className="py-space-1">{pt.time}</td>
                  <td className="py-space-1">{pt.fatiguedCount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
};
