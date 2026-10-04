import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';
import { AdminDashboardScreen } from '../screens/AdminDashboardScreen';
import { ManageStudentsScreen } from '../screens/ManageStudentsScreen';
import { ManageTeachersScreen } from '../screens/ManageTeachersScreen';
import { ManageClassroomsScreen } from '../screens/ManageClassroomsScreen';
import { SystemStatusScreen } from '../screens/SystemStatusScreen';
import { ApiService } from '../services/api';

jest.mock('../services/api');

describe('Phase 23: Admin Screens, Management & System Status', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders AdminDashboardScreen with system metrics and infrastructure health', async () => {
    (ApiService.getTeachers as jest.Mock).mockResolvedValueOnce([{}, {}]);
    (ApiService.getStudents as jest.Mock).mockResolvedValueOnce([{}, {}, {}]);
    (ApiService.getClassrooms as jest.Mock).mockResolvedValueOnce([{}]);
    (ApiService.getSessions as jest.Mock).mockResolvedValueOnce([
      { status: 'Monitoring' },
    ]);
    (ApiService.getSystemStatus as jest.Mock).mockResolvedValueOnce({
      ai_server: 'Online',
      database: 'Online',
      api: 'Online',
      cameras: [{ id: 'CAM-001', state: 'Online' }],
    });

    const { getByText } = await render(<AdminDashboardScreen />);

    await waitFor(() => {
      expect(getByText('Admin Dashboard')).toBeTruthy();
      expect(getByText('Teachers')).toBeTruthy();
      expect(getByText('2')).toBeTruthy();
      expect(getByText('Students')).toBeTruthy();
      expect(getByText('3')).toBeTruthy();
      expect(getByText('Infrastructure Health')).toBeTruthy();
      expect(getByText('AI Server:')).toBeTruthy();
    });
  });

  it('surfaces validation errors during student creation per Phase 23 pass condition', async () => {
    (ApiService.getStudents as jest.Mock).mockResolvedValueOnce([]);

    const { getByText, getByPlaceholderText } = await render(<ManageStudentsScreen />);

    await waitFor(() => {
      expect(getByText('Student Management')).toBeTruthy();
    });

    // Attempt submitting without required fields
    await act(async () => {
      fireEvent.press(getByText('Add Student'));
    });

    await waitFor(() => {
      expect(getByText('Student ID and Name are required.')).toBeTruthy();
    });

    // Now fill fields and simulate backend validation error
    await act(async () => {
      fireEvent.changeText(getByPlaceholderText('Student ID (e.g. S045)'), 'S045');
      fireEvent.changeText(getByPlaceholderText('Full Name'), 'John Doe');
    });

    (ApiService.createStudent as jest.Mock).mockRejectedValueOnce({
      response: { data: { detail: 'Duplicate student_id already registered.' } },
    });

    await act(async () => {
      fireEvent.press(getByText('Add Student'));
    });

    await waitFor(() => {
      expect(
        getByText('Duplicate student_id already registered.')
      ).toBeTruthy();
    });
  });

  it('surfaces validation errors during teacher creation', async () => {
    (ApiService.getTeachers as jest.Mock).mockResolvedValueOnce([]);

    const { getByText } = await render(<ManageTeachersScreen />);

    await waitFor(() => {
      expect(getByText('Teacher Management')).toBeTruthy();
    });

    await act(async () => {
      fireEvent.press(getByText('Add Teacher'));
    });

    await waitFor(() => {
      expect(getByText('Name and Email are required.')).toBeTruthy();
    });
  });

  it('renders ManageClassroomsScreen with camera ID associations', async () => {
    (ApiService.getClassrooms as jest.Mock).mockResolvedValueOnce([
      {
        id: 1,
        name: 'AI Lab 01',
        camera_id: 'CAM-001',
        is_active: true,
      },
    ]);

    const { getByText } = await render(<ManageClassroomsScreen />);

    await waitFor(() => {
      expect(getByText('AI Lab 01')).toBeTruthy();
      expect(getByText('CAM-001')).toBeTruthy();
      expect(getByText('Camera ID:')).toBeTruthy();
    });
  });

  it('clearly displays offline services in SystemStatusScreen so "no alerts" is not misread', async () => {
    (ApiService.getSystemStatus as jest.Mock).mockResolvedValueOnce({
      ai_server: 'Offline',
      database: 'Online',
      api: 'Online',
      cameras: [
        { id: 'CAM-001', state: 'Online' },
        { id: 'CAM-003', state: 'Offline' },
      ],
      fps: 0.0,
      model_mode: 'heuristic',
      privacy_mode: true,
    });

    const { getByText, getAllByText } = await render(<SystemStatusScreen />);

    await waitFor(() => {
      // Offline banner alert must be visible per APP-21 / APP-25
      expect(getByText('⚠ AI Service Unavailable')).toBeTruthy();
      expect(getByText('⚠ Camera Offline')).toBeTruthy();

      // Specific camera state
      expect(getByText('CAM-003')).toBeTruthy();
      expect(getAllByText('Offline').length).toBeGreaterThanOrEqual(1);
    });
  });
});
