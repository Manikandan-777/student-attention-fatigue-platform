import React, { useState, useEffect, useRef } from 'react';
import {
  Camera,
  Eye,
  EyeOff,
  Play,
  Square,
  Search,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
  Users,
  AlertTriangle,
  Smile,
  Frown,
} from 'lucide-react';
import { StudentTile } from './StudentTile';
import { TrackResult, VideoFrameMessage } from '../types';
import { STATUS_MAPPING, TOKENS } from '../tokens';
import apiClient from '../api/client';
import { API_BASE_URL } from '../config';

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
  const [cameraRunning, setCameraRunning] = useState(false);
  const [cameraMode, setCameraMode] = useState<'1000_faces' | 'webcam'>('webcam');
  const [privacyOverride, setPrivacyOverride] = useState<boolean | null>(null);
  const [filter, setFilter] = useState<'all' | 'fatigued' | 'attentive' | 'distracted'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 24;

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Check camera status on mount
  useEffect(() => {
    apiClient
      .get('/camera/status')
      .then((res) => {
        if (res.data?.is_running) {
          setCameraRunning(true);
          setCameraMode(res.data.mode);
          setPrivacyOverride(false);
        }
      })
      .catch(() => {});
  }, []);

  const handleStartCamera = async (mode: '1000_faces' | 'webcam') => {
    try {
      await apiClient.post('/camera/start', {
        mode,
        camera_index: 0,
        privacy_mode: false,
      });
      setCameraRunning(true);
      setCameraMode(mode);
      setPrivacyOverride(false);
    } catch (err) {
      console.error('Failed to start camera:', err);
    }
  };

  const handleStopCamera = async () => {
    try {
      await apiClient.post('/camera/stop');
      setCameraRunning(false);
    } catch (err) {
      console.error('Failed to stop camera:', err);
    }
  };

  const handleTogglePrivacy = async () => {
    try {
      const res = await apiClient.post('/camera/toggle-privacy');
      setPrivacyOverride(res.data.privacy_mode);
    } catch {
      setPrivacyOverride((prev) => !prev);
    }
  };

  const isPrivacyActive = privacyOverride !== null ? privacyOverride : privacyMode;

  // Video Frame WebSocket Canvas fallback
  useEffect(() => {
    if (isPrivacyActive || !videoFrame || !videoFrame.jpeg_b64) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);

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

        ctx.fillStyle = color;
        const labelText = `ID ${t.track_id}: ${t.attention_status}`;
        ctx.font = '12px Outfit, sans-serif';
        const textWidth = ctx.measureText(labelText).width;
        ctx.fillRect(bx, Math.max(0, by - 18), textWidth + 8, 18);

        ctx.fillStyle = TOKENS.colors['bg-surface'];
        ctx.fillText(labelText, bx + 4, Math.max(14, by - 4));
      });
    };
    img.src = `data:image/jpeg;base64,${videoFrame.jpeg_b64}`;
  }, [videoFrame, isPrivacyActive]);

  // Filtering and Searching
  const filteredTracks = tracks.filter((t) => {
    if (filter === 'fatigued' && t.fatigue_status !== 'Fatigued') return false;
    if (filter === 'attentive' && t.attention_status !== 'Attentive') return false;
    if (filter === 'distracted' && t.attention_status !== 'Distracted') return false;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      const matchLabel = t.label?.toLowerCase().includes(q);
      const matchId = String(t.track_id).includes(q);
      return matchLabel || matchId;
    }
    return true;
  });

  const totalPages = Math.max(1, Math.ceil(filteredTracks.length / pageSize));
  const displayedTracks = filteredTracks.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const fatiguedTotal = tracks.filter((t) => t.fatigue_status === 'Fatigued').length;
  const attentiveTotal = tracks.filter((t) => t.attention_status === 'Attentive').length;
  const distractedTotal = tracks.filter((t) => t.attention_status === 'Distracted').length;

  return (
    <div className="space-y-space-6">
      {/* Header and Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-4 border-b border-border-subtle pb-space-4">
        <div className="flex items-center space-x-space-4">
          <div className="p-space-2 rounded-radius-lg bg-bg-info text-accent-primary">
            <Camera className="w-5 h-5" aria-hidden="true" />
          </div>
          <div>
            <div className="flex items-center space-x-space-3">
              <h2 className="text-lg font-bold text-text-primary">
                Student Monitoring Grid
              </h2>
              <span className="text-xs bg-bg-info text-accent-primary font-semibold px-space-3 py-space-1 rounded-radius-pill border border-accent-primary">
                {tracks.length} Detected
              </span>
            </div>
            <p className="text-xs text-text-secondary mt-0.5">
              Ultra-scale multi-face tracking & real-time fatigue indicator detection
            </p>
          </div>
        </div>

        {/* Live Camera Controls */}
        <div className="flex flex-wrap items-center gap-space-2">
          {/* Mode Switcher */}
          <div className="inline-flex rounded-radius-md border border-border-subtle bg-bg-surface p-0.5 text-xs font-semibold">
            <button
              onClick={() => {
                setCameraMode('webcam');
                handleStartCamera('webcam');
              }}
              className={`px-space-3 py-space-1 rounded-radius-sm transition-colors ${
                cameraMode === 'webcam'
                  ? 'bg-accent-primary text-white shadow-sm'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              Live Webcam (Real Faces)
            </button>
            <button
              onClick={() => {
                setCameraMode('1000_faces');
                handleStartCamera('1000_faces');
              }}
              className={`px-space-3 py-space-1 rounded-radius-sm transition-colors ${
                cameraMode === '1000_faces'
                  ? 'bg-accent-primary text-white shadow-sm'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              1,000 Faces Demo (Synthetic)
            </button>
          </div>

          {/* Start/Stop Button */}
          {cameraRunning ? (
            <button
              onClick={handleStopCamera}
              className="inline-flex items-center space-x-space-1 px-space-3 py-space-2 text-xs font-semibold text-accent-danger bg-bg-surface border border-accent-danger rounded-radius-md hover:bg-accent-danger hover:text-white transition-colors"
            >
              <Square className="w-3.5 h-3.5" />
              <span>Stop Stream</span>
            </button>
          ) : (
            <button
              onClick={() => handleStartCamera(cameraMode)}
              className="inline-flex items-center space-x-space-1 px-space-3 py-space-2 text-xs font-semibold text-white bg-accent-primary rounded-radius-md hover:bg-opacity-90 shadow-sm transition-colors"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Start Camera</span>
            </button>
          )}

          {/* Privacy Preview Toggle */}
          <button
            onClick={handleTogglePrivacy}
            className="inline-flex items-center space-x-space-1 px-space-3 py-space-2 text-xs font-semibold text-text-secondary bg-bg-surface border border-border-subtle rounded-radius-md hover:text-text-primary transition-colors"
            title="Toggle video preview on/off"
          >
            {isPrivacyActive ? (
              <>
                <Eye className="w-3.5 h-3.5" />
                <span>Show Video</span>
              </>
            ) : (
              <>
                <EyeOff className="w-3.5 h-3.5" />
                <span>Hide Video</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Privacy Mode Notice */}
      {isPrivacyActive && (
        <div
          className="flex items-center space-x-space-2 text-xs font-semibold text-text-secondary bg-bg-surface border border-border-subtle px-space-4 py-space-2 rounded-radius-md"
          role="status"
        >
          <ShieldAlert className="w-4 h-4 text-accent-primary" aria-hidden="true" />
          <span>Video disabled (privacy mode)</span>
        </div>
      )}

      {/* Video View (when privacy mode is false) */}
      {!isPrivacyActive && (cameraRunning || videoFrame) && (
        <div className="bg-bg-surface border border-border-subtle rounded-radius-xl p-space-4 shadow-sm overflow-hidden flex justify-center">
          {cameraRunning ? (
            <img
              src={`${API_BASE_URL}/camera/feed?mode=${cameraMode}&t=${cameraRunning ? 'live' : 'off'}`}
              alt="Live Classroom Camera Stream"
              className="max-w-full h-auto rounded-radius-lg border border-border-subtle max-h-[540px]"
            />
          ) : (
            <canvas
              ref={canvasRef}
              className="max-w-full h-auto rounded-radius-lg border border-border-subtle"
              aria-label="Annotated classroom video stream with student bounding boxes"
            />
          )}
        </div>
      )}

      {/* Filter and Search Bar */}
      {tracks.length > 0 && (
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-space-3 pt-space-2">
          <div className="flex flex-wrap items-center gap-space-2">
            <button
              onClick={() => { setFilter('all'); setCurrentPage(1); }}
              className={`px-space-3 py-space-1.5 text-xs font-semibold rounded-radius-md transition-colors ${
                filter === 'all'
                  ? 'bg-accent-primary text-white'
                  : 'bg-bg-surface border border-border-subtle text-text-secondary hover:text-text-primary'
              }`}
            >
              All Tracks ({tracks.length})
            </button>
            <button
              onClick={() => { setFilter('fatigued'); setCurrentPage(1); }}
              className={`inline-flex items-center space-x-1 px-space-3 py-space-1.5 text-xs font-semibold rounded-radius-md transition-colors ${
                filter === 'fatigued'
                  ? 'bg-accent-danger text-white'
                  : 'bg-bg-surface border border-border-subtle text-accent-danger hover:bg-accent-danger hover:text-white'
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Fatigued ({fatiguedTotal})</span>
            </button>
            <button
              onClick={() => { setFilter('attentive'); setCurrentPage(1); }}
              className={`inline-flex items-center space-x-1 px-space-3 py-space-1.5 text-xs font-semibold rounded-radius-md transition-colors ${
                filter === 'attentive'
                  ? 'bg-accent-success text-white'
                  : 'bg-bg-surface border border-border-subtle text-accent-success hover:bg-accent-success hover:text-white'
              }`}
            >
              <Smile className="w-3.5 h-3.5" />
              <span>Attentive ({attentiveTotal})</span>
            </button>
            <button
              onClick={() => { setFilter('distracted'); setCurrentPage(1); }}
              className={`inline-flex items-center space-x-1 px-space-3 py-space-1.5 text-xs font-semibold rounded-radius-md transition-colors ${
                filter === 'distracted'
                  ? 'bg-amber-500 text-white'
                  : 'bg-bg-surface border border-border-subtle text-amber-500 hover:bg-amber-500 hover:text-white'
              }`}
            >
              <Frown className="w-3.5 h-3.5" />
              <span>Distracted ({distractedTotal})</span>
            </button>
          </div>

          {/* Search Input */}
          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-text-muted" />
            <input
              type="text"
              placeholder="Search student ID (e.g. S0012)..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full pl-9 pr-space-3 py-space-1.5 text-xs bg-bg-surface border border-border-subtle rounded-radius-md text-text-primary focus:outline-none focus:border-accent-primary"
            />
          </div>
        </div>
      )}

      {/* Grid of Student Tiles */}
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
        <div className="space-y-space-4">
          <div
            className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-space-4"
            role="region"
            aria-label="Student status tiles"
          >
            {displayedTracks.map((track) => (
              <StudentTile
                key={track.track_id}
                track={track}
                isSelected={selectedTrackId === track.track_id}
                onClick={() => onSelectTrack?.(track.track_id)}
              />
            ))}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-border-subtle pt-space-4 text-xs text-text-secondary">
              <div>
                Showing {(currentPage - 1) * pageSize + 1} to{' '}
                {Math.min(currentPage * pageSize, filteredTracks.length)} of{' '}
                {filteredTracks.length} students
              </div>
              <div className="flex items-center space-x-space-2">
                <button
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  className="p-space-2 border border-border-subtle rounded-radius-md disabled:opacity-40 hover:bg-bg-surface"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="font-semibold text-text-primary">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  className="p-space-2 border border-border-subtle rounded-radius-md disabled:opacity-40 hover:bg-bg-surface"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
