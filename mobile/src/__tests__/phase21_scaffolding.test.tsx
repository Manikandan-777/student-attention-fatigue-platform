import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';
import { LoginScreen } from '../screens/LoginScreen';
import { OfflineBanner } from '../components/OfflineBanner';
import { StorageService } from '../services/storage';
import { ApiService } from '../services/api';
import * as SecureStore from 'expo-secure-store';

jest.mock('../services/api');

describe('Phase 21: Mobile Scaffolding, Auth & Navigation', () => {
  beforeEach(async () => {
    jest.clearAllMocks();
    await StorageService.clearAuth();
  });

  it('renders login screen with required inputs and action button per APP-3', async () => {
    const onLoginSuccess = jest.fn();
    const { getByPlaceholderText, getByText } = await render(
      <LoginScreen onLoginSuccess={onLoginSuccess} />
    );

    expect(getByText('AI MONITOR')).toBeTruthy();
    expect(getByPlaceholderText('teacher_1 or admin')).toBeTruthy();
    expect(getByPlaceholderText('••••••••')).toBeTruthy();
    expect(getByText('LOGIN')).toBeTruthy();
  });

  it('stores JWT token securely in expo-secure-store and never plain storage', async () => {
    (ApiService.login as jest.Mock).mockResolvedValueOnce({
      access_token: 'secret-jwt-token-123',
      role: 'teacher',
      token_type: 'bearer',
    });

    const onLoginSuccess = jest.fn();
    const { getByPlaceholderText, getByText } = await render(
      <LoginScreen onLoginSuccess={onLoginSuccess} />
    );

    await act(async () => {
      fireEvent.changeText(getByPlaceholderText('teacher_1 or admin'), 'teacher_1');
      fireEvent.changeText(getByPlaceholderText('••••••••'), 'pass123');
    });

    await act(async () => {
      fireEvent.press(getByText('LOGIN'));
    });

    await waitFor(() => {
      expect(SecureStore.setItemAsync).toHaveBeenCalledWith(
        'auth_jwt_token',
        'secret-jwt-token-123'
      );
      expect(onLoginSuccess).toHaveBeenCalledWith('teacher');
    });
  });

  it('failed login surfaces exact message per APP-25: "Invalid username or password."', async () => {
    (ApiService.login as jest.Mock).mockRejectedValueOnce(
      new Error('Unauthorized')
    );

    const onLoginSuccess = jest.fn();
    const { getByPlaceholderText, getByText } = await render(
      <LoginScreen onLoginSuccess={onLoginSuccess} />
    );

    await act(async () => {
      fireEvent.changeText(getByPlaceholderText('teacher_1 or admin'), 'baduser');
      fireEvent.changeText(getByPlaceholderText('••••••••'), 'badpass');
    });

    await act(async () => {
      fireEvent.press(getByText('LOGIN'));
    });

    await waitFor(() => {
      // APP-25 exact specification
      expect(getByText('Invalid username or password.')).toBeTruthy();
    });
  });

  it('displays network offline banner with exact text per APP-25', async () => {
    const { getByText } = await render(<OfflineBanner isNetworkOffline={true} />);

    expect(getByText('No Internet Connection')).toBeTruthy();
    expect(getByText('Showing the latest available data.')).toBeTruthy();
  });

  it('displays camera offline banner with exact text per APP-25', async () => {
    const { getByText } = await render(<OfflineBanner isCameraOffline={true} />);

    expect(getByText('⚠ Camera Offline')).toBeTruthy();
    expect(
      getByText('The classroom camera is currently unavailable.\n\nAI monitoring has been paused.')
    ).toBeTruthy();
  });

  it('displays AI service unavailable banner with exact text per APP-25', async () => {
    const { getByText } = await render(<OfflineBanner isAiOffline={true} />);

    expect(getByText('⚠ AI Service Unavailable')).toBeTruthy();
    expect(getByText('New predictions are currently unavailable.')).toBeTruthy();
  });
});
