import React, { useEffect, useRef } from 'react';
import { TOKENS } from '../../tokens';
import { LiveTrackResult } from './types';

interface OverlayCanvasProps {
  tracks: LiveTrackResult[];
  width: number;
  height: number;
  mirrored?: boolean;
}

export function toCanvasRect(
  [x, y, w, h]: [number, number, number, number],
  canvasW: number,
  canvasH: number,
  mirrored: boolean = true
) {
  const nx = mirrored ? 1 - (x + w) : x;
  return {
    x: nx * canvasW,
    y: y * canvasH,
    w: w * canvasW,
    h: h * canvasH,
  };
}

export const OverlayCanvas: React.FC<OverlayCanvasProps> = ({
  tracks,
  width,
  height,
  mirrored = true,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const lastDrawTimeRef = useRef(Date.now());

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, width, height);

    if (tracks.length === 0) return;

    lastDrawTimeRef.current = Date.now();

    tracks.forEach((track) => {
      const rect = toCanvasRect(track.bbox, width, height, mirrored);

      // Determine bounding box color based on attention/fatigue status
      let statusColor: string = TOKENS.colors['accent-success'];
      if (track.warming_up || track.attention_status === 'Unknown') {
        statusColor = TOKENS.colors['text-secondary'];
      } else if (track.fatigue_status === 'Fatigued') {
        statusColor = TOKENS.colors['accent-danger'];
      } else if (track.attention_status === 'Distracted') {
        statusColor = TOKENS.colors['accent-primary'];
      }

      // 1. Draw Bounding Box
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = statusColor;
      ctx.strokeRect(rect.x, rect.y, rect.w, rect.h);

      // 2. Draw Label background tag
      const statusText = track.warming_up
        ? `${track.label} · Warm-up`
        : `${track.label} · ${track.attention_status} · ${track.fatigue_status}`;

      ctx.font = 'bold 12px Outfit, sans-serif';
      const textMetrics = ctx.measureText(statusText);
      const tagH = 20;
      const tagW = textMetrics.width + 12;
      const tagY = Math.max(0, rect.y - tagH);

      ctx.fillStyle = TOKENS.colors['bg-surface'];
      ctx.fillRect(rect.x, tagY, tagW, tagH);

      ctx.strokeStyle = statusColor;
      ctx.lineWidth = 1;
      ctx.strokeRect(rect.x, tagY, tagW, tagH);

      // 3. Draw Unmirrored Text
      ctx.fillStyle = statusColor;
      ctx.fillText(statusText, rect.x + 6, tagY + 14);
    });
  }, [tracks, width, height, mirrored]);

  // Clear stale overlay if no results received for 2 seconds
  useEffect(() => {
    const timer = window.setInterval(() => {
      if (Date.now() - lastDrawTimeRef.current > 2000 && canvasRef.current) {
        const ctx = canvasRef.current.getContext('2d');
        if (ctx) {
          ctx.clearRect(0, 0, width, height);
        }
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [width, height]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 pointer-events-none w-full h-full"
      aria-hidden="true"
    />
  );
};
