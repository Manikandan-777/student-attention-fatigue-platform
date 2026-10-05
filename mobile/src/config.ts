import Constants from 'expo-constants';
import { Platform } from 'react-native';

const getDevHost = (): string => {
  // 1. Automatically detect development machine IP when running on physical phone via Expo Go
  const hostUri =
    Constants.expoConfig?.hostUri ||
    (Constants as any).manifest?.debuggerHost ||
    (Constants as any).manifest2?.extra?.expoClient?.hostUri;

  if (hostUri) {
    const ip = hostUri.split(':')[0];
    if (ip && ip !== 'localhost' && ip !== '127.0.0.1') {
      return `${ip}:8000`;
    }
  }

  // 2. Android Emulator fallback
  if (Platform.OS === 'android') {
    return '10.0.2.2:8000';
  }

  // 3. Web and desktop fallback
  return 'localhost:8000';
};

const DEV_HOST = getDevHost();

export const API_BASE_URL = `http://${DEV_HOST}`;
export const WS_BASE_URL = `ws://${DEV_HOST}`;
export const WS_TELEMETRY_URL = `${WS_BASE_URL}/ws/telemetry`;
