import * as SecureStore from 'expo-secure-store';

const TOKEN_KEY = 'auth_jwt_token';
const ROLE_KEY = 'auth_user_role';
const USERNAME_KEY = 'auth_username';

export const StorageService = {
  async saveAuth(token: string, role: string, username: string): Promise<void> {
    try {
      await SecureStore.setItemAsync(TOKEN_KEY, token);
      await SecureStore.setItemAsync(ROLE_KEY, role);
      await SecureStore.setItemAsync(USERNAME_KEY, username);
    } catch {
      // Fallback in-memory storage for test/environment where native module isn't linked
      (globalThis as unknown as { __mockStorage?: Record<string, string> }).__mockStorage = {
        [TOKEN_KEY]: token,
        [ROLE_KEY]: role,
        [USERNAME_KEY]: username,
      };
    }
  },

  async getToken(): Promise<string | null> {
    try {
      return await SecureStore.getItemAsync(TOKEN_KEY);
    } catch {
      const mock = (globalThis as unknown as { __mockStorage?: Record<string, string> }).__mockStorage;
      return mock ? mock[TOKEN_KEY] ?? null : null;
    }
  },

  async getRole(): Promise<string | null> {
    try {
      return await SecureStore.getItemAsync(ROLE_KEY);
    } catch {
      const mock = (globalThis as unknown as { __mockStorage?: Record<string, string> }).__mockStorage;
      return mock ? mock[ROLE_KEY] ?? null : null;
    }
  },

  async getUsername(): Promise<string | null> {
    try {
      return await SecureStore.getItemAsync(USERNAME_KEY);
    } catch {
      const mock = (globalThis as unknown as { __mockStorage?: Record<string, string> }).__mockStorage;
      return mock ? mock[USERNAME_KEY] ?? null : null;
    }
  },

  async clearAuth(): Promise<void> {
    try {
      await SecureStore.deleteItemAsync(TOKEN_KEY);
      await SecureStore.deleteItemAsync(ROLE_KEY);
      await SecureStore.deleteItemAsync(USERNAME_KEY);
    } catch {
      const mock = (globalThis as unknown as { __mockStorage?: Record<string, string> }).__mockStorage;
      if (mock) {
        delete mock[TOKEN_KEY];
        delete mock[ROLE_KEY];
        delete mock[USERNAME_KEY];
      }
    }
  },
};
