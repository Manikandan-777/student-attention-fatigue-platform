import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { getErrorMessage } from '../errors';
import { toCanvasRect } from '../OverlayCanvas';
import { ConsentNotice } from '../ConsentNotice';
import { ResultsPanel } from '../ResultsPanel';
import { LiveTrackResult } from '../types';
import { LiveCameraButton } from '../LiveCameraButton';

describe('Live Camera Feature Tests (Phase LC-4, LC-5)', () => {
  describe('Error Message Mapping', () => {
    it('returns exact human-readable copy for all standard error codes', () => {
      expect(getErrorMessage('INSECURE_CONTEXT')).toContain('HTTPS');
      expect(getErrorMessage('PERMISSION_DENIED')).toContain('Camera permission was blocked');
      expect(getErrorMessage('NOT_FOUND')).toContain('No camera found');
      expect(getErrorMessage('BUSY')).toContain('in use by another app');
      expect(getErrorMessage('4403')).toContain('not enabled on this server');
      expect(getErrorMessage('4429')).toContain('busy');
      expect(getErrorMessage('4408')).toContain('inactivity');
      expect(getErrorMessage('4413')).toContain('too high');
    });
  });

  describe('Canvas Coordinate Transformation', () => {
    it('mirrors x-axis correctly for mirrored selfie preview', () => {
      const bbox: [number, number, number, number] = [0.2, 0.1, 0.3, 0.4];
      const canvasW = 640;
      const canvasH = 480;

      // When mirrored: nx = 1 - (x + w) = 1 - (0.2 + 0.3) = 0.5
      const rect = toCanvasRect(bbox, canvasW, canvasH, true);
      expect(rect.x).toBeCloseTo(0.5 * 640);
      expect(rect.y).toBeCloseTo(0.1 * 480);
      expect(rect.w).toBeCloseTo(0.3 * 640);
      expect(rect.h).toBeCloseTo(0.4 * 480);
    });

    it('preserves x-axis when unmirrored', () => {
      const bbox: [number, number, number, number] = [0.2, 0.1, 0.3, 0.4];
      const rect = toCanvasRect(bbox, 640, 480, false);
      expect(rect.x).toBeCloseTo(0.2 * 640);
      expect(rect.y).toBeCloseTo(0.1 * 480);
    });
  });

  describe('ConsentNotice Component', () => {
    it('renders privacy notice and calls onAccept on click', () => {
      const onAccept = vi.fn();
      const onCancel = vi.fn();

      render(<ConsentNotice onAccept={onAccept} onCancel={onCancel} />);

      expect(screen.getByText(/Privacy & Consent Notice/i)).toBeInTheDocument();
      expect(screen.getByText(/never recorded or stored/i)).toBeInTheDocument();

      const startBtn = screen.getByRole('button', { name: /Start Camera/i });
      fireEvent.click(startBtn);
      expect(onAccept).toHaveBeenCalledOnce();
    });
  });

  describe('ResultsPanel Component', () => {
    const mockTracks: LiveTrackResult[] = [
      {
        track_id: 1,
        label: 'S001',
        bbox: [0.1, 0.1, 0.2, 0.2],
        bbox_normalized: true,
        warming_up: false,
        attention_status: 'Attentive',
        fatigue_status: 'Normal',
        attention_score: 88.0,
        fatigue_index: 0.15,
        confidence: 0.95,
        expression: { top: 'Neutral', confidence: 0.82 },
      },
      {
        track_id: 2,
        label: 'S002',
        bbox: [0.5, 0.1, 0.2, 0.2],
        bbox_normalized: true,
        warming_up: true,
        attention_status: 'Unknown',
        fatigue_status: 'Unknown',
        attention_score: 50.0,
        fatigue_index: 0.20,
        confidence: 0.90,
        expression: null,
      },
    ];

    it('renders detected face cards with correct badges and warm-up state', () => {
      render(<ResultsPanel tracks={mockTracks} latencyMs={45} />);

      expect(screen.getByText(/Detected Faces \(2\)/i)).toBeInTheDocument();
      expect(screen.getByText('S001')).toBeInTheDocument();
      expect(screen.getByText('S002')).toBeInTheDocument();

      // S001 has status badges
      expect(screen.getByText('Attentive')).toBeInTheDocument();
      expect(screen.getByText('Normal')).toBeInTheDocument();

      // S002 is warming up
      expect(screen.getByText(/Collecting data to establish baseline/i)).toBeInTheDocument();

      // Ethical footer is present (D8)
      expect(screen.getByText(/Indicators to support teacher observation/i)).toBeInTheDocument();
    });
  });

  describe('LiveCameraButton Component', () => {
    it('renders button and opens dialog upon user click', () => {
      render(<LiveCameraButton />);

      const button = screen.getByRole('button', { name: /Open live camera detection dialog/i });
      expect(button).toBeInTheDocument();

      fireEvent.click(button);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
  });
});
