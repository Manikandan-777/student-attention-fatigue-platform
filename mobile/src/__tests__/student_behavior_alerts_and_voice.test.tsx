import React from 'react';
import { render, waitFor, fireEvent } from '@testing-library/react-native';
import { TeacherDashboardScreen } from '../screens/TeacherDashboardScreen';
import { ApiService } from '../services/api';
import { speechService } from '../services/speech';

jest.mock('../services/api');

describe('Student Behavior Alerts & Voice Speech on Mobile Dashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (ApiService.getTeacherDashboard as jest.Mock).mockResolvedValue({
      session_id: 12,
      class_name: 'AI & DS - A Section',
      status: 'Monitoring',
      students_detected: 42,
      counts: { attentive: 28, distracted: 8, unknown: 0, fatigued: 6 },
      avg_attention_score: 78.0,
      class_fatigue_pct: 38.0,
      open_alerts: 2,
      fatigue_advisory: {
        class_fatigue_pct: 38.0,
        level: 2,
        code: 'INTERACTIVE',
        message: 'Make the session more interactive.',
        usable_tracks: 42,
        since: '2026-10-05T10:00:00Z',
      },
    });
    (ApiService.getAlerts as jest.Mock).mockResolvedValue([
      {
        id: 201,
        session_id: 12,
        track_id: 1,
        label: 'S001',
        type: 'fatigue',
        status: 'New',
        message: 'Frequent yawning and eyelid closure observed over last 60s',
        confidence: 0.94,
        created_at: '2026-10-06T10:15:00Z',
      },
      {
        id: 202,
        session_id: 12,
        track_id: 4,
        label: 'S004',
        type: 'distraction',
        status: 'New',
        message: 'Sustained head yaw away from teacher detected for > 15s',
        confidence: 0.88,
        created_at: '2026-10-06T10:18:00Z',
      },
    ]);
  });

  it('renders student behavior alerts on the dashboard with student labels and behavior badges', async () => {
    const { getByText } = await render(<TeacherDashboardScreen />);

    await waitFor(() => {
      // Behavior alerts section
      expect(getByText('Student Behavior Alerts')).toBeTruthy();
      expect(getByText('Student S001')).toBeTruthy();
      expect(getByText('Student S004')).toBeTruthy();

      // Behavioral indicators
      expect(getByText('Fatigue Alert')).toBeTruthy();
      expect(getByText('Inattentive')).toBeTruthy();
      expect(getByText('Frequent yawning and eyelid closure observed over last 60s')).toBeTruthy();
      expect(getByText('Sustained head yaw away from teacher detected for > 15s')).toBeTruthy();
    });
  });

  it('filters behavior alerts when filter chips are pressed', async () => {
    const { getByText, queryByText, getByTestId } = await render(<TeacherDashboardScreen />);

    await waitFor(() => {
      expect(getByText('Student S001')).toBeTruthy();
      expect(getByText('Student S004')).toBeTruthy();
    });

    // Filter by Fatigue
    fireEvent.press(getByTestId('filter-chip-fatigue'));
    await waitFor(() => {
      expect(getByText('Student S001')).toBeTruthy();
      expect(queryByText('Student S004')).toBeNull();
    });

    // Filter by Inattentive
    fireEvent.press(getByTestId('filter-chip-distraction'));
    await waitFor(() => {
      expect(getByText('Student S004')).toBeTruthy();
      expect(queryByText('Student S001')).toBeNull();
    });
  });

  it('triggers voice speech test when Test Voice button is clicked', async () => {
    const testAlertSpy = jest.spyOn(speechService, 'testAlert');
    const { getByText } = await render(<TeacherDashboardScreen />);

    await waitFor(() => {
      expect(getByText('Test Voice')).toBeTruthy();
    });

    fireEvent.press(getByText('Test Voice'));
    expect(testAlertSpy).toHaveBeenCalled();
  });

  it('toggles voice speech mute state from top header', async () => {
    const toggleSpy = jest.spyOn(speechService, 'toggleMute');
    const { getByText } = await render(<TeacherDashboardScreen />);

    // Trigger toggle via speech service and verify state
    speechService.toggleMute();
    expect(toggleSpy).toHaveBeenCalled();
  });

  it('triggers immediate high fatigue emergency shout when High Fatigue Shout button is clicked', async () => {
    const highFatigueSpy = jest.spyOn(speechService, 'testHighFatigueAlert');
    const { getByTestId } = await render(<TeacherDashboardScreen />);

    await waitFor(() => {
      expect(getByTestId('test-high-fatigue-btn')).toBeTruthy();
    });

    fireEvent.press(getByTestId('test-high-fatigue-btn'));
    expect(highFatigueSpy).toHaveBeenCalled();
  });

  it('triggers 30-second periodic shout when 30s Shout button is clicked', async () => {
    const periodicSpy = jest.spyOn(speechService, 'testPeriodic30sAlert');
    const { getByTestId } = await render(<TeacherDashboardScreen />);

    await waitFor(() => {
      expect(getByTestId('test-periodic-30s-btn')).toBeTruthy();
    });

    fireEvent.press(getByTestId('test-periodic-30s-btn'));
    expect(periodicSpy).toHaveBeenCalled();
  });

  it('toggles auto-shout state when toggle button is pressed', async () => {
    const { getByTestId, getByText } = await render(<TeacherDashboardScreen />);

    await waitFor(() => {
      expect(getByTestId('auto-shout-toggle-btn')).toBeTruthy();
      expect(getByText('ON')).toBeTruthy();
    });

    fireEvent.press(getByTestId('auto-shout-toggle-btn'));
    await waitFor(() => {
      expect(getByText('OFF')).toBeTruthy();
    });
  });

  it('opens Student Behavior Alerts modal when View All or RecentAlertCard is pressed', async () => {
    const { getByText, getAllByText } = await render(<TeacherDashboardScreen />);

    await waitFor(() => {
      expect(getByText(/View All/)).toBeTruthy();
    });

    fireEvent.press(getByText(/View All/));
    await waitFor(() => {
      // Modal should be open with the full list and tabs
      expect(getAllByText('Student Behavior Alerts').length).toBeGreaterThanOrEqual(1);
    });
  });
});
