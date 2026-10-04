import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { TeacherDashboardScreen } from '../screens/TeacherDashboardScreen';
import { StudentDetailScreen } from '../screens/StudentDetailScreen';
import { AlertCenterScreen } from '../screens/AlertCenterScreen';
import { SessionReportScreen } from '../screens/SessionReportScreen';
import { RootNavigator } from '../navigation/RootNavigator';
import { ApiService } from '../services/api';
import { StorageService } from '../services/storage';
import { TrackResultLite } from '../types';

jest.mock('../services/api');

const mockStudent: TrackResultLite = {
  track_id: 3,
  label: 'S003',
  attention_status: 'Attentive',
  fatigue_status: 'Fatigued',
  attention_score: 85.0,
  confidence: 0.92,
};

describe('Phase 22: Teacher Screens & Scoping', () => {
  beforeEach(async () => {
    jest.clearAllMocks();
    await StorageService.clearAuth();
  });

  it('renders TeacherDashboard with current session metrics and quick navigation', async () => {
    (ApiService.getTeacherDashboard as jest.Mock).mockResolvedValueOnce({
      session_id: 12,
      class_name: 'III AI & DS',
      status: 'Monitoring',
      students_detected: 45,
      counts: { attentive: 35, distracted: 7, unknown: 0, fatigued: 3 },
      avg_attention_score: 82.0,
      open_alerts: 3,
    });

    const onNavigate = jest.fn();
    const { getByText } = await render(
      <TeacherDashboardScreen onNavigate={onNavigate} />
    );

    await waitFor(() => {
      expect(getByText('Good Morning, Teacher')).toBeTruthy();
      expect(getByText('Class: III AI & DS')).toBeTruthy();
      expect(getByText('Status: Monitoring')).toBeTruthy();
      expect(getByText('Students: 45')).toBeTruthy();
      expect(getByText('35')).toBeTruthy(); // Attentive
      expect(getByText('7')).toBeTruthy();  // Distracted
      expect(getByText('3')).toBeTruthy();  // Fatigued
    });

    fireEvent.press(getByText('[ View Students ]'));
    expect(onNavigate).toHaveBeenCalledWith('Students');
  });

  it('renders StudentDetailScreen without exposing raw CNN/LSTM internals per APP-9', async () => {
    const onViewReport = jest.fn();
    const { getByText, queryByText } = await render(
      <StudentDetailScreen student={mockStudent} onViewReport={onViewReport} />
    );

    expect(getByText('Student S003')).toBeTruthy();
    expect(getByText('Attentive')).toBeTruthy();
    expect(getByText('Fatigued')).toBeTruthy();
    expect(getByText('92%')).toBeTruthy();

    // Verify AI internals are NOT exposed per APP-9 and APP-27
    expect(queryByText(/weights/i)).toBeNull();
    expect(queryByText(/logits/i)).toBeNull();
    expect(queryByText(/embedding/i)).toBeNull();
    expect(queryByText(/lstm/i)).toBeNull();
  });

  it('renders AlertCenterScreen with action buttons to transition alert status', async () => {
    (ApiService.getAlerts as jest.Mock).mockResolvedValueOnce([
      {
        id: 77,
        session_id: 12,
        track_id: 3,
        label: 'S003',
        type: 'fatigue',
        status: 'New',
        message: 'Repeated fatigue-related indicators during the current session.',
        confidence: 0.92,
        created_at: '2026-10-03T10:42:11Z',
      },
    ]);

    (ApiService.updateAlertStatus as jest.Mock).mockResolvedValueOnce({
      id: 77,
      status: 'Viewed',
      message: 'Repeated fatigue-related indicators during the current session.',
    });

    const { getByText } = await render(<AlertCenterScreen />);

    await waitFor(() => {
      expect(getByText('⚠ Student S003')).toBeTruthy();
      expect(getByText(/fatigue-related indicators/i)).toBeTruthy();
      expect(getByText('Mark Viewed')).toBeTruthy();
      expect(getByText('Resolve')).toBeTruthy();
    });

    fireEvent.press(getByText('Mark Viewed'));
    await waitFor(() => {
      expect(ApiService.updateAlertStatus).toHaveBeenCalledWith(77, 'Viewed');
    });
  });

  it('renders SessionReportScreen with aggregates and mandatory ethical notice', async () => {
    (ApiService.getReports as jest.Mock).mockResolvedValueOnce([
      {
        session_id: 12,
        class_name: 'III AI & DS',
        date: '2026-10-03',
        start: '09:00',
        end: '10:00',
        duration_min: 60,
        students: 45,
        attention: { attentive: 35, distracted: 7, unknown: 0 },
        fatigue: { normal: 42, fatigued: 3 },
        alerts_total: 5,
        avg_attention_score: 82.0,
        per_student: [],
      },
    ]);

    const { getByText } = await render(<SessionReportScreen />);

    await waitFor(() => {
      expect(getByText('CLASSROOM SESSION REPORT')).toBeTruthy();
      expect(getByText('Class: III AI & DS')).toBeTruthy();
      expect(getByText('Duration: 60 minutes')).toBeTruthy();
      expect(getByText(/AI-generated indicators to support teacher observation/i)).toBeTruthy();
    });
  });

  it('enforces role scoping: teacher cannot access admin navigation tabs', async () => {
    await StorageService.saveAuth('mock-token', 'teacher', 'prof_smith');

    const { getByText, queryByText } = await render(<RootNavigator />);

    await waitFor(() => {
      // Teacher navigation tabs present
      expect(getByText('Dashboard')).toBeTruthy();
      expect(getByText('Students')).toBeTruthy();
      expect(getByText('Alerts')).toBeTruthy();
      expect(getByText('Reports')).toBeTruthy();
      expect(getByText('Profile')).toBeTruthy();

      // Admin tabs MUST NOT be present
      expect(queryByText('Teachers')).toBeNull();
      expect(queryByText('Classrooms')).toBeNull();
      expect(queryByText('Status')).toBeNull();
    });
  });
});
