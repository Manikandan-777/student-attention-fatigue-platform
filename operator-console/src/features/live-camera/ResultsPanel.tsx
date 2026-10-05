import React from 'react';
import { StatusBadge } from '../../components/StatusBadge';
import { LiveTrackResult } from './types';
import { Info, User } from 'lucide-react';

interface ResultsPanelProps {
  tracks: LiveTrackResult[];
  latencyMs: number;
}

export const ResultsPanel: React.FC<ResultsPanelProps> = ({ tracks, latencyMs }) => {
  return (
    <div className="flex flex-col h-full space-y-space-4">
      {/* Hidden live region announcing status & count changes */}
      <div className="sr-only" aria-live="polite">
        {tracks.length === 0
          ? 'No faces currently detected in view.'
          : `${tracks.length} ${tracks.length === 1 ? 'face' : 'faces'} detected.`}
      </div>

      <div className="flex items-center justify-between pb-space-2 border-b border-border-subtle">
        <h4 className="text-sm font-bold text-text-primary flex items-center">
          <User className="w-4 h-4 mr-space-2 text-accent-primary" />
          Detected Faces ({tracks.length})
        </h4>
        <span className="text-xs text-text-muted">
          Latency: {latencyMs} ms
        </span>
      </div>

      {tracks.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center p-space-6 text-center text-text-muted border border-dashed border-border-subtle rounded-radius-lg">
          <p className="text-xs font-medium">No face detected.</p>
          <p className="text-xs mt-space-1 text-text-secondary">
            Position yourself facing the camera in good lighting.
          </p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto space-y-space-3 pr-space-1">
          {tracks.map((track) => (
            <div
              key={track.track_id}
              className="p-space-3 bg-bg-surface border border-border-subtle rounded-radius-lg shadow-sm space-y-space-2 text-xs"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-text-primary">{track.label}</span>
                <span className="text-text-muted">
                  Confidence: {Math.round(track.confidence * 100)}%
                </span>
              </div>

              {track.warming_up ? (
                <div className="p-space-2 bg-bg-info text-accent-primary rounded-radius-md text-xs font-medium">
                  Collecting data to establish baseline (warm-up)...
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-space-2">
                  <div>
                    <span className="text-text-muted block mb-space-1">Attention:</span>
                    <StatusBadge status={track.attention_status} size="sm" />
                  </div>
                  <div>
                    <span className="text-text-muted block mb-space-1">Fatigue:</span>
                    <StatusBadge status={track.fatigue_status} size="sm" />
                  </div>
                </div>
              )}

              {/* Expression Chip */}
              <div className="pt-space-1 border-t border-border-subtle flex items-center justify-between text-text-secondary">
                <span>Expression (indicator):</span>
                <span className="font-semibold text-text-body">
                  {track.expression
                    ? `${track.expression.top} (${Math.round(track.expression.confidence * 100)}%)`
                    : 'Not clear'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Ethical guidance footer (D8, D10) */}
      <div className="pt-space-3 border-t border-border-subtle text-xs text-text-muted flex items-start space-x-space-2">
        <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-text-secondary" />
        <p>
          Mode: heuristic. Indicators to support teacher observation, not a diagnosis or disciplinary record.
        </p>
      </div>
    </div>
  );
};
