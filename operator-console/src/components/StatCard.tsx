import React from 'react';

interface StatCardProps {
  label: string;
  value: number | string;
  subtext?: string;
  icon?: React.ReactNode;
}

export const StatCard: React.FC<StatCardProps> = ({ label, value, subtext, icon }) => {
  return (
    <div className="bg-bg-surface border border-border-subtle rounded-radius-xl p-space-6 shadow-sm flex flex-col justify-between">
      <div className="flex items-center justify-between mb-space-2">
        <span className="text-text-secondary text-sm font-medium">{label}</span>
        {icon && <div className="text-text-secondary">{icon}</div>}
      </div>
      <div className="text-text-primary text-xl font-bold tracking-tight">
        {value}
      </div>
      {subtext && (
        <div className="text-text-muted text-xs mt-space-1">{subtext}</div>
      )}
    </div>
  );
};
