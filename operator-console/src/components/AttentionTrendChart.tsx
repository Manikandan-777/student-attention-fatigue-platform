import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { TOKENS } from '../tokens';

export interface AttentionDataPoint {
  time: string;
  avgAttention: number;
  studentAttention?: number;
}

interface AttentionTrendChartProps {
  data: AttentionDataPoint[];
  selectedStudentLabel?: string | null;
}

export const AttentionTrendChart: React.FC<AttentionTrendChartProps> = ({
  data,
  selectedStudentLabel,
}) => {
  const latestAvg = data.length > 0 ? data[data.length - 1].avgAttention : 0;

  return (
    <div className="bg-bg-surface border border-border-subtle rounded-radius-xl p-space-6 shadow-sm space-y-space-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-bold text-text-primary">
            Attention Score Trend
          </h3>
          <p className="text-xs text-text-secondary">
            Real-time average across active tracks
            {selectedStudentLabel && ` & ${selectedStudentLabel}`}
          </p>
        </div>
        <div className="text-right">
          <span className="text-xs text-text-muted">Current Avg</span>
          <div className="text-lg font-bold text-text-primary">
            {Math.round(latestAvg)}%
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
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke={TOKENS.colors['border-subtle']} />
              <XAxis
                dataKey="time"
                stroke={TOKENS.colors['text-muted']}
                tick={{ fontSize: 11 }}
              />
              <YAxis
                domain={[0, 100]}
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
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line
                type="monotone"
                dataKey="avgAttention"
                name="Class Average"
                stroke={TOKENS.colors['accent-primary']}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
              {selectedStudentLabel && (
                <Line
                  type="monotone"
                  dataKey="studentAttention"
                  name={selectedStudentLabel}
                  stroke={TOKENS.colors['accent-success']}
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Screen reader text table alternative */}
      <details className="text-xs text-text-muted pt-space-2">
        <summary className="cursor-pointer font-medium hover:text-text-body">
          Accessible data view (tabular)
        </summary>
        <div className="max-h-32 overflow-y-auto mt-space-2 border border-border-subtle rounded-radius-md p-space-2">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-border-subtle">
                <th className="py-space-1">Time</th>
                <th className="py-space-1">Class Avg</th>
                {selectedStudentLabel && <th className="py-space-1">{selectedStudentLabel}</th>}
              </tr>
            </thead>
            <tbody>
              {data.slice(-10).map((pt, i) => (
                <tr key={i} className="border-b border-border-subtle">
                  <td className="py-space-1">{pt.time}</td>
                  <td className="py-space-1">{Math.round(pt.avgAttention)}%</td>
                  {selectedStudentLabel && (
                    <td className="py-space-1">{Math.round(pt.studentAttention ?? 0)}%</td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
};
