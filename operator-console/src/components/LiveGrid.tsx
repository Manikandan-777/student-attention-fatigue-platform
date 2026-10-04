import React, { useEffect, useRef } from 'react';
import { ShieldAlert, Users } from 'lucide-react';
import { StudentTile } from './StudentTile';
import { TrackResult, VideoFrameMessage } from '../types';
import { STATUS_MAPPING, TOKENS } from '../tokens';

interface LiveGridProps {
  tracks: TrackResult[];
  videoFrame?: VideoFrameMessage | null;
  privacyMode: boolean;
  onSelectTrack?: (trackId: number) => void;
  selectedTrackId?: number | null;
}

export const LiveGrid: React.FC<LiveGridProps> = ({
  tracks,
  videoFrame,
  privacyMode,
  onSelectTrack,
  selectedTrackId,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (privacyMode || !videoFrame || !videoFrame.jpeg_b64) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);

      // Draw bounding boxes and status labels
      videoFrame.tracks.forEach((t) => {
        const [x, y, w, h] = t.bbox;
        const norm = w <= 1 && h <= 1;
        const bx = norm ? x * canvas.width : x;
        const by = norm ? y * canvas.height : y;
        const bw = norm ? w * canvas.width : w;
        const bh = norm ? h * canvas.height : h;

        const statusKey = t.attention_status in STATUS_MAPPING ? t.attention_status : 'Unknown';
        const color = STATUS_MAPPING[statusKey].borderColor;

        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(bx, by, bw, bh);

        // Label tag background
        ctx.fillStyle = color;
        const labelText = `ID ${t.track_id}: ${t.attention_status}`;
        ctx.font = '12px Outfit, sans-serif';
        const textWidth = ctx.measureText(labelText).width;
        ctx.fillRect(bx, Math.max(0, by - 18), textWidth + 8, 18);

        // Label text
        ctx.fillStyle = TOKENS.colors['bg-surface'];
        ctx.fillText(labelText, bx + 4, Math.max(14, by - 4));
      });
    };
    img.src = `data:image/jpeg;base64,${videoFrame.jpeg_b64}`;
  }, [videoFrame, privacyMode]);

  return (
    <div className="space-y-space-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-space-4">
          <Users className="w-5 h-5 text-accent-primary" aria-hidden="true" />
          <h2 className="text-lg font-bold text-text-primary">
            Student Monitoring Grid
          </h2>
          <span className="text-xs bg-bg-info text-accent-primary font-semibold px-space-3 py-space-1 rounded-radius-pill border border-accent-primary">
            {tracks.length} Detected
          </span>
        </div>

        {privacyMode && (
          <div
            className="flex items-center space-x-space-2 text-xs font-semibold text-text-secondary bg-bg-surface border border-border-subtle px-space-4 py-space-2 rounded-radius-md"
            role="status"
          >
            <ShieldAlert className="w-4 h-4 text-accent-primary" aria-hidden="true" />
            <span>Video disabled (privacy mode)</span>
          </div>
        )}
      </div>

      {/* Video view (when privacyMode is false) */}
      {!privacyMode && videoFrame && (
        <div className="bg-bg-surface border border-border-subtle rounded-radius-xl p-space-4 shadow-sm overflow-hidden flex justify-center">
          <canvas
            ref={canvasRef}
            className="max-w-full h-auto rounded-radius-lg border border-border-subtle"
            aria-label="Annotated classroom video stream with student bounding boxes"
          />
        </div>
      )}

      {/* Grid of Student Tiles (Always active, serving as fallback or alongside video) */}
      {tracks.length === 0 ? (
        <div className="bg-bg-surface border border-border-subtle rounded-radius-xl p-space-12 text-center shadow-sm">
          <Users className="w-10 h-10 text-text-muted mx-auto mb-space-4" aria-hidden="true" />
          <h3 className="text-base font-semibold text-text-primary mb-space-1">
            No active student tracks
          </h3>
          <p className="text-sm text-text-secondary">
            No students are currently detected in this session.
          </p>
        </div>
      ) : (
        <div
          className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-space-6"
          role="region"
          aria-label="Student status tiles"
        >
          {tracks.map((track) => (
            <StudentTile
              key={track.track_id}
              track={track}
              isSelected={selectedTrackId === track.track_id}
              onClick={() => onSelectTrack?.(track.track_id)}
            />
          ))}
        </div>
      )}
    </div>
  );
};
