import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { LiveGrid } from '../components/LiveGrid';
import { StudentTile } from '../components/StudentTile';
import { TrackResult, VideoFrameMessage } from '../types';

const mockTracks: TrackResult[] = [
  {
    track_id: 1,
    label: 'S001',
    bbox: [0.1, 0.1, 0.2, 0.3],
    bbox_normalized: true,
    landmark_confidence: 0.98,
    attention_score: 92.0,
    fatigue_index: 0.1,
    attention_status: 'Attentive',
    fatigue_status: 'Normal',
    confidence: 0.95,
    model_mode: 'heuristic',
  },
  {
    track_id: 2,
    label: 'S002',
    bbox: [0.4, 0.2, 0.2, 0.3],
    bbox_normalized: true,
    landmark_confidence: 0.94,
    attention_score: 45.0,
    fatigue_index: 0.2,
    attention_status: 'Distracted',
    fatigue_status: 'Normal',
    confidence: 0.88,
    model_mode: 'heuristic',
  },
  {
    track_id: 3,
    label: 'S003',
    bbox: [0.7, 0.2, 0.2, 0.3],
    bbox_normalized: true,
    landmark_confidence: 0.91,
    attention_score: 60.0,
    fatigue_index: 0.85,
    attention_status: 'Attentive',
    fatigue_status: 'Fatigued',
    confidence: 0.92,
    model_mode: 'heuristic',
  },
];

describe('Phase 18: Multi-Face Live Grid', () => {
  it('renders student tile with correct labels, status badges and attention score', () => {
    const onSelect = vi.fn();
    render(<StudentTile track={mockTracks[0]} onClick={onSelect} />);

    expect(screen.getByText('S001')).toBeInTheDocument();
    expect(screen.getByText('ID: 1')).toBeInTheDocument();
    expect(screen.getByText('Attentive')).toBeInTheDocument();
    expect(screen.getByText('Normal')).toBeInTheDocument();
    expect(screen.getByText('92%')).toBeInTheDocument();
    expect(screen.getByText('95%')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button'));
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it('renders privacy mode fallback tile view with privacy notice', () => {
    render(
      <LiveGrid
        tracks={mockTracks}
        privacyMode={true}
      />
    );

    // Privacy notice visible
    expect(screen.getByText(/Video disabled \(privacy mode\)/i)).toBeInTheDocument();

    // Renders all student tiles
    expect(screen.getByText('S001')).toBeInTheDocument();
    expect(screen.getByText('S002')).toBeInTheDocument();
    expect(screen.getByText('S003')).toBeInTheDocument();
  });

  it('handles empty state when zero tracks are detected', () => {
    render(
      <LiveGrid
        tracks={[]}
        privacyMode={true}
      />
    );

    expect(screen.getByText(/No active student tracks/i)).toBeInTheDocument();
    expect(
      screen.getByText(/No students are currently detected in this session/i)
    ).toBeInTheDocument();
  });

  it('renders canvas element when privacyMode is false and video frame is provided', () => {
    const mockFrame: VideoFrameMessage = {
      type: 'frame',
      session_id: 12,
      ts: '2026-10-03T10:00:00Z',
      jpeg_b64: 'fake-base64-image-data',
      tracks: [
        {
          track_id: 1,
          bbox: [0.1, 0.1, 0.2, 0.3],
          attention_status: 'Attentive',
          fatigue_status: 'Normal',
        },
      ],
    };

    render(
      <LiveGrid
        tracks={mockTracks}
        videoFrame={mockFrame}
        privacyMode={false}
      />
    );

    expect(screen.queryByText(/Video disabled \(privacy mode\)/i)).not.toBeInTheDocument();
    const canvas = screen.getByLabelText(/Annotated classroom video stream/i);
    expect(canvas).toBeInTheDocument();
  });

  it('allows selecting a track tile via click and keyboard', () => {
    const onSelect = vi.fn();
    render(
      <LiveGrid
        tracks={mockTracks}
        privacyMode={true}
        selectedTrackId={2}
        onSelectTrack={onSelect}
      />
    );

    const tile2 = screen.getByLabelText(/Student S002/i);
    expect(tile2).toBeInTheDocument();
    expect(tile2).toHaveClass('ring-2 ring-accent-primary');

    fireEvent.keyDown(tile2, { key: 'Enter', code: 'Enter' });
    expect(onSelect).toHaveBeenCalledWith(2);
  });
});
