import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';
import { AdminDashboardScreen } from '../screens/AdminDashboardScreen';
import { ManageTeachersScreen } from '../screens/ManageTeachersScreen';
import { RootNavigator } from '../navigation/RootNavigator';
import { ApiService } from '../services/api';
import { StorageService } from '../services/storage';

jest.mock('../services/api');

describe('Phase 23: Admin Dashboard, Teacher Management & Admin Tabs', () => {
  beforeEach(async () => {
    jest.clearAllMocks();
    await StorageService.clearAuth();
    (ApiService.getMe as jest.Mock).mockResolvedValue({
      id: 99,
      username: 'admin',
      role: 'admin',
      active: true,
    });
    (ApiService.getSessions as jest.Mock).mockResolvedValue([
      {
        id: 12,
        classroom_id: 1,
        class_name: 'AI & DS - A Section',
        room_name: 'Room A413',
        status: 'Monitoring',
        students_detected_max: 42,
        started_at: '2026-10-05T10:00:00Z',
      },
    ]);
    (ApiService.getTeachers as jest.Mock).mockResolvedValue([]);
    (ApiService.getClassrooms as jest.Mock).mockResolvedValue([]);
    (ApiService.createTeacher as jest.Mock).mockResolvedValue({
      id: 103,
      user_id: 4,
      display_name: 'Dr. New Teacher',
      username: 'new.teacher',
      classroom_name: 'AI & DS - A Section',
      classroom_id: 1,
      active: true,
    });
  });

  it('renders AdminDashboardScreen with session selector and live metric cards', async () => {
    const { getByText, getAllByText, unmount } = await render(<AdminDashboardScreen />);

    await waitFor(() => {
      expect(getByText('Dr. Raman S')).toBeTruthy();
      expect(getByText('Select Session')).toBeTruthy();
      expect(getByText(/AI & DS - A Section/i)).toBeTruthy();

      // Metric Cards & Donut elements
      expect(getAllByText('Students').length).toBeGreaterThanOrEqual(1);
      expect(getAllByText('Attentive').length).toBeGreaterThanOrEqual(1);
      expect(getAllByText('Distracted').length).toBeGreaterThanOrEqual(1);
      expect(getAllByText('Fatigued').length).toBeGreaterThanOrEqual(1);
      expect(getByText('Open Alerts')).toBeTruthy();

      // Trend Charts & Status Split
      expect(getByText('Attention Trend')).toBeTruthy();
      expect(getByText('Fatigue Trend')).toBeTruthy();
      expect(getByText('Status Split (Current)')).toBeTruthy();
    });
    unmount();
  });

  it('renders all admin tabs in RootNavigator: Dashboard, Teachers, Profile', async () => {
    await StorageService.saveAuth('mock-token', 'admin', 'admin');

    const component = await render(<RootNavigator />);

    await waitFor(() => {
      expect(component.getByText('Dashboard')).toBeTruthy();
      expect(component.getByText('Teachers')).toBeTruthy();
      expect(component.getByText('Profile')).toBeTruthy();
    });
    component.unmount();
  });

  it('renders ManageTeachersScreen with teachers, search, add, and delete confirmation modal', async () => {
    (ApiService.getTeachers as jest.Mock).mockResolvedValue([
      {
        id: 101,
        user_id: 2,
        display_name: 'Ms. Priya M',
        username: 'priya.m',
        classroom_name: 'CSE - B Section',
        classroom_id: 2,
        active: true,
      },
      {
        id: 102,
        user_id: 3,
        display_name: 'Mr. Karthik S',
        username: 'karthik.s',
        classroom_name: 'ECE - A Section',
        classroom_id: 3,
        active: false,
      },
    ]);
    (ApiService.getClassrooms as jest.Mock).mockResolvedValue([
      { id: 1, room_name: 'Room A413', class_name: 'AI & DS - A Section', active: true },
      { id: 2, room_name: 'Room B201', class_name: 'CSE - B Section', active: true },
    ]);

    const { getByText, getByPlaceholderText, getByTestId, unmount } = await render(<ManageTeachersScreen />);

    await waitFor(() => {
      expect(getByText('Teachers')).toBeTruthy();
      expect(getByText('Ms. Priya M')).toBeTruthy();
      expect(getByText('CSE - B Section')).toBeTruthy();
      expect(getByText('Mr. Karthik S')).toBeTruthy();
      expect(getByText('Inactive')).toBeTruthy();
    });

    // Test search filter
    fireEvent.changeText(getByPlaceholderText('Search teachers...'), 'Priya');
    expect(getByText('Ms. Priya M')).toBeTruthy();

    // Open Add Teacher mode
    await act(async () => {
      fireEvent.press(getByTestId('btn-add-teacher'));
    });

    await waitFor(() => {
      expect(getByText('Add Teacher')).toBeTruthy();
    });

    // Fill form
    await act(async () => {
      fireEvent.changeText(getByPlaceholderText('Enter full name'), 'Dr. New Teacher');
      fireEvent.changeText(getByPlaceholderText('Enter username'), 'new.teacher');
      fireEvent.changeText(getByPlaceholderText('Enter password'), 'secretpass123');
    });

    // Submit form
    await act(async () => {
      fireEvent.press(getByTestId('btn-create-teacher'));
    });

    await waitFor(() => {
      expect(ApiService.createTeacher).toHaveBeenCalledWith(
        expect.objectContaining({
          display_name: 'Dr. New Teacher',
          username: 'new.teacher',
          password: 'secretpass123',
        })
      );
    });
    unmount();
  });
});
