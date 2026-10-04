import React from 'react';
import { StatusBadge } from './StatusBadge';
import { TrackResult } from '../types';

interface StudentTileProps {
  track: TrackResult;
  onClick?: () => void;
  isSelected?: boolean;
}

export const StudentTile: React.FC<StudentTileProps> = ({
  track,
  onClick,
  isSelected = false,
}) => {
  const selectionClass = isSelected
    ? 'ring-2 ring-accent-primary'
    : 'hover:border-border-strong';

  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick?.();
        }
      }}
      aria-label={`Student ${track.label}, Attention: ${track.attention_status}, Fatigue: ${track.fatigue_status}`}
      className={`bg-bg-surface border border-border-subtle rounded-radius-xl p-space-6 shadow-sm flex flex-col justify-between cursor-pointer transition-all ${selectionClass}`}
    >
      <div className="flex items-center justify-between mb-space-4">
        <span className="text-text-primary text-base font-bold tracking-tight">
          {track.label}
        </span>
        <span className="text-text-muted text-xs">
          ID: {track.track_id}
        </span>
      </div>

      <div className="flex flex-wrap gap-space-2 mb-space-4">
        <StatusBadge status={track.attention_status} size="sm" />
        <StatusBadge status={track.fatigue_status} size="sm" />
      </div>

      <div className="space-y-space-2">
        <div className="flex justify-between items-center text-xs">
          <span className="text-text-secondary">Attention Score</span>
          <span className="text-text-primary font-semibold">
            {Math.round(track.attention_score)}%
          </span>
        </div>
        <div className="w-full bg-border-subtle rounded-radius-pill h-2 overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${
              track.attention_status === 'Attentive'
                ? 'bg-accent-success'
                : track.attention_status === 'Distracted'
                ? 'bg-accent-primary'
                : 'bg-text-muted'
            }`}
            style={{ width: `${Math.max(0, Math.min(100, track.attention_score))}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-text-muted pt-space-1">
          <span>Confidence</span>
          <span>{Math.round(track.confidence * 100)}%</span>
        </div>
      </div>
    </div>
  );
};
