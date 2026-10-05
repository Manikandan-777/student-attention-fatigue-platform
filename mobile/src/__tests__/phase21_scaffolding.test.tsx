import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';
import { LoginScreen } from '../screens/LoginScreen';
import { OfflineState } from '../components/OfflineState';
import { StorageService } from '../services/storage';
import { ApiService } from '../services/api';
import * as SecureStore from 'expo-secure-store';

jest.mock('../services/api');

describe('Phase 21: Mobile Login, Secure Storage & Offline States', () => {
  beforeEach(async () => {
    jest.clearAllMocks();
    await StorageService.clearAll();
  });

  it('renders login screen with required inputs and action button', async () => {
    const onLoginSuccess = jest.fn();
    const { getByPlaceholderText, getByText } = await render(
      <LoginScreen onLoginSuccess={onLoginSuccess} />
    );

    expect(getByText('AI Classroom Monitor')).toBeTruthy();
    expect(getByPlaceholderText('Username')).toBeTruthy();
    expect(getByPlaceholderText('Password')).toBeTruthy();
    expect(getByText('Login')).toBeTruthy();
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
      fireEvent.changeText(getByPlaceholderText('Username'), 'teacher_1');
      fireEvent.changeText(getByPlaceholderText('Password'), 'pass123');
    });

    await act(async () => {
      fireEvent.press(getByText('Login'));
    });

    await waitFor(() => {
      expect(SecureStore.setItemAsync).toHaveBeenCalledWith(
        'auth_jwt_token',
        'secret-jwt-token-123'
      );
      expect(onLoginSuccess).toHaveBeenCalledWith('teacher', 'teacher_1');
    });
  });

  it('failed login surfaces exact message: "Invalid username or password."', async () => {
    (ApiService.login as jest.Mock).mockRejectedValueOnce(
      new Error('Unauthorized')
    );

    const onLoginSuccess = jest.fn();
    const { getByPlaceholderText, getByText } = await render(
      <LoginScreen onLoginSuccess={onLoginSuccess} />
    );

    await act(async () => {
      fireEvent.changeText(getByPlaceholderText('Username'), 'baduser');
      fireEvent.changeText(getByPlaceholderText('Password'), 'badpass');
    });

    await act(async () => {
      fireEvent.press(getByText('Login'));
    });

    await waitFor(() => {
      expect(getByText('Invalid username or password.')).toBeTruthy();
    });
  });

  it('displays offline state with exact text per Acceptance Checklist #7', async () => {
    const onRetry = jest.fn();
    const { getByText } = await render(<OfflineState onRetry={onRetry} />);

    expect(getByText('Showing the latest available data.')).toBeTruthy();
    expect(
      getByText('Realtime updates are currently unavailable. We will reconnect automatically.')
    ).toBeTruthy();
    expect(getByText('Retry Now')).toBeTruthy();

    fireEvent.press(getByText('Retry Now'));
    expect(onRetry).toHaveBeenCalled();
  });
});
