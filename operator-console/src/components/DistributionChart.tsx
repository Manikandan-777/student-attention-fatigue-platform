import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { TOKENS } from '../tokens';

interface DistributionChartProps {
  counts: {
    attentive: number;
    distracted: number;
    fatigued: number;
    unknown: number;
  };
}

export const DistributionChart: React.FC<DistributionChartProps> = ({ counts }) => {
  const data = [
    { name: 'Attentive', count: counts.attentive, color: TOKENS.colors['accent-success'] },
    { name: 'Distracted', count: counts.distracted, color: TOKENS.colors['accent-primary'] },
    { name: 'Fatigued', count: counts.fatigued, color: TOKENS.colors['accent-danger'] },
    { name: 'Unknown', count: counts.unknown, color: TOKENS.colors['text-secondary'] },
  ];

  const total = counts.attentive + counts.distracted + counts.fatigued + counts.unknown;

  return (
    <div className="bg-bg-surface border border-border-subtle rounded-radius-xl p-space-6 shadow-sm space-y-space-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-bold text-text-primary">
            Student Status Distribution
          </h3>
          <p className="text-xs text-text-secondary">
            Current session breakdown across states
          </p>
        </div>
        <div className="text-right">
          <span className="text-xs text-text-muted">Total Active</span>
          <div className="text-lg font-bold text-text-primary">{total}</div>
        </div>
      </div>

      <div className="h-64 w-full">
        {total === 0 ? (
          <div className="h-full flex items-center justify-center text-sm text-text-muted">
            No students currently in session.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke={TOKENS.colors['border-subtle']} />
              <XAxis
                dataKey="name"
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
              <Bar dataKey="count" isAnimationActive={false}>
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Screen reader text alternative */}
      <details className="text-xs text-text-muted pt-space-2">
        <summary className="cursor-pointer font-medium hover:text-text-body">
          Accessible summary table
        </summary>
        <div className="mt-space-2 border border-border-subtle rounded-radius-md p-space-2">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-border-subtle">
                <th className="py-space-1">State</th>
                <th className="py-space-1">Count</th>
                <th className="py-space-1">Percentage</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row, i) => (
                <tr key={i} className="border-b border-border-subtle">
                  <td className="py-space-1">{row.name}</td>
                  <td className="py-space-1">{row.count}</td>
                  <td className="py-space-1">
                    {total > 0 ? Math.round((row.count / total) * 100) : 0}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
};
