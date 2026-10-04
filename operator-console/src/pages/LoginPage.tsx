import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, Lock, User, AlertCircle } from 'lucide-react';
import apiClient from '../api/client';
import { useAuthStore } from '../store/authStore';

export const LoginPage: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setErrorMsg('Please enter both username and password.');
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);

    try {
      const response = await apiClient.post('/auth/login', {
        username: username.trim(),
        password: password.trim(),
      });

      const { access_token, role } = response.data;
      login(access_token, role, username.trim());
      navigate('/');
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      const detail = error.response?.data?.detail;
      setErrorMsg(detail ?? 'Invalid username or password. Please verify your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg-surface flex items-center justify-center p-space-6">
      <div className="max-w-md w-full bg-bg-surface border border-border-subtle rounded-radius-xl p-space-8 shadow-sm space-y-space-6">
        <div className="text-center space-y-space-2">
          <div className="w-12 h-12 bg-bg-info text-accent-primary rounded-radius-xl mx-auto flex items-center justify-center">
            <Activity className="w-6 h-6" />
          </div>
          <h1 className="text-xl font-bold text-text-primary tracking-tight">
            Sign In to ClassAware
          </h1>
          <p className="text-sm text-text-secondary">
            Attention & Fatigue Monitoring Operator Console
          </p>
        </div>

        {errorMsg && (
          <div
            role="alert"
            className="flex items-center space-x-space-3 bg-bg-surface border border-accent-danger text-accent-danger p-space-4 rounded-radius-lg text-sm"
          >
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-space-4">
          <div className="space-y-space-2">
            <label
              htmlFor="username"
              className="block text-sm font-semibold text-text-body"
            >
              Username
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-space-3 flex items-center pointer-events-none text-text-muted">
                <User className="w-4 h-4" />
              </div>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full pl-space-10 pr-space-4 py-space-2 text-sm border border-border-strong rounded-radius-lg focus:outline-none focus:ring-2 focus:ring-accent-primary text-text-primary bg-bg-surface"
                placeholder="teacher_1 or admin"
              />
            </div>
          </div>

          <div className="space-y-space-2">
            <label
              htmlFor="password"
              className="block text-sm font-semibold text-text-body"
            >
              Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-space-3 flex items-center pointer-events-none text-text-muted">
                <Lock className="w-4 h-4" />
              </div>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full pl-space-10 pr-space-4 py-space-2 text-sm border border-border-strong rounded-radius-lg focus:outline-none focus:ring-2 focus:ring-accent-primary text-text-primary bg-bg-surface"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-space-3 text-sm font-bold text-bg-surface bg-accent-primary rounded-radius-lg hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-accent-primary disabled:opacity-50 transition-opacity shadow-sm"
          >
            {isLoading ? 'Signing In...' : 'Sign In'}
          </button>
        </form>

        <div className="text-center text-xs text-text-muted pt-space-2">
          Authorized personnel only. Sessions are logged and audited.
        </div>
      </div>
    </div>
  );
};
