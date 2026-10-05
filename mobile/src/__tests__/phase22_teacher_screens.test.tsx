import React from 'react';
import { render, waitFor, fireEvent } from '@testing-library/react-native';
import { TeacherDashboardScreen } from '../screens/TeacherDashboardScreen';
import { TeacherProfileScreen } from '../screens/TeacherProfileScreen';
import { RootNavigator } from '../navigation/RootNavigator';
import { ApiService } from '../services/api';
import { StorageService } from '../services/storage';

jest.mock('../services/api');

describe('Phase 22: Teacher Dashboard, Profile & Role Scoping', () => {
  beforeEach(async () => {
    jest.clearAllMocks();
    await StorageService.clearAuth();
    (ApiService.getMe as jest.Mock).mockResolvedValue({
      id: 1,
      username: 'aravind.k',
      role: 'teacher',
      active: true,
    });
    (ApiService.getTeacherDashboard as jest.Mock).mockResolvedValue(null);
  });

  it('renders TeacherDashboard with 5 stat cards, trend charts, and status split per UI design', async () => {
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

    const { getByText, getAllByText } = await render(<TeacherDashboardScreen />);

    await waitFor(() => {
      // Current Class & Welcome
      expect(getByText('AI & DS - A Section')).toBeTruthy();
      expect(getByText('Mr. Aravind K')).toBeTruthy();

      // 5 Stat Cards & Donut numbers
      expect(getAllByText('42').length).toBeGreaterThanOrEqual(1); // Students count
      expect(getAllByText('28').length).toBeGreaterThanOrEqual(1); // Attentive
      expect(getAllByText('8').length).toBeGreaterThanOrEqual(1);  // Distracted
      expect(getAllByText('6').length).toBeGreaterThanOrEqual(1);  // Fatigued
      expect(getAllByText('2').length).toBeGreaterThanOrEqual(1);  // Open Alerts

      // Fatigue Advisory Banner
      expect(getByText('Make the session more interactive.')).toBeTruthy();
      expect(getByText('Class fatigue score is 38%.')).toBeTruthy();

      // Live Trend Charts & Status Split
      expect(getByText('Attention Trend')).toBeTruthy();
      expect(getByText('Fatigue Trend')).toBeTruthy();
      expect(getByText('Status Split (Current)')).toBeTruthy();
      expect(getByText('Recent Alert Count')).toBeTruthy();
    });
  });

  it('renders Profile screen with user information and log out button', async () => {
    const onLogout = jest.fn();
    const { getByText } = await render(
      <TeacherProfileScreen
        role="teacher"
        username="aravind.k"
        displayName="Mr. Aravind K"
        classroomName="AI & DS - A Section"
        onLogout={onLogout}
      />
    );

    expect(getByText('Profile')).toBeTruthy();
    expect(getByText('Mr. Aravind K')).toBeTruthy();
    expect(getByText('Teacher')).toBeTruthy();
    expect(getByText('aravind.k')).toBeTruthy();
    expect(getByText('AI & DS - A Section')).toBeTruthy();

    fireEvent.press(getByText('Log out'));
    expect(onLogout).toHaveBeenCalled();
  });

  it('enforces role scoping: teacher only sees Dashboard and Profile tabs (no Teachers tab)', async () => {
    await StorageService.saveAuth('mock-token', 'teacher', 'aravind.k');

    const { getByText, queryByText } = await render(<RootNavigator />);

    await waitFor(() => {
      // Teacher navigation tabs present per spec §2
      expect(getByText('Dashboard')).toBeTruthy();
      expect(getByText('Profile')).toBeTruthy();

      // Admin tabs MUST NOT be present
      expect(queryByText('Teachers')).toBeNull();
    });
  });
});
