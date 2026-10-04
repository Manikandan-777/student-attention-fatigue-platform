import { create } from 'zustand';

interface AuthState {
  token: string | null;
  role: string | null;
  username: string | null;
  login: (token: string, role: string, username: string) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: sessionStorage.getItem('auth_token'),
  role: sessionStorage.getItem('auth_role'),
  username: sessionStorage.getItem('auth_username'),

  login: (token: string, role: string, username: string) => {
    sessionStorage.setItem('auth_token', token);
    sessionStorage.setItem('auth_role', role);
    sessionStorage.setItem('auth_username', username);
    set({ token, role, username });
  },

  logout: () => {
    sessionStorage.removeItem('auth_token');
    sessionStorage.removeItem('auth_role');
    sessionStorage.removeItem('auth_username');
    set({ token: null, role: null, username: null });
  },

  isAuthenticated: () => !!get().token,
}));
