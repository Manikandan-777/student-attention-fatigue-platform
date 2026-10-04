import React from 'react';
import { LogOut, User } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { StatusBadge } from './StatusBadge';

interface HeaderProps {
  sessionTitle?: string;
  isOnline?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  sessionTitle = 'Active Monitoring Session',
  isOnline = true,
}) => {
  const { username, role, logout } = useAuthStore();

  return (
    <header className="h-16 bg-bg-surface border-b border-border-subtle px-space-8 flex items-center justify-between shadow-sm">
      <div className="flex items-center space-x-space-4">
        <h2 className="text-base font-bold text-text-primary">
          {sessionTitle}
        </h2>
        <StatusBadge status={isOnline ? 'Online' : 'Offline'} size="sm" />
      </div>

      <div className="flex items-center space-x-space-6">
        <div className="flex items-center space-x-space-3">
          <div className="w-8 h-8 rounded-radius-pill bg-bg-info text-accent-primary flex items-center justify-center font-bold text-xs">
            <User className="w-4 h-4" />
          </div>
          <div className="text-left">
            <p className="text-sm font-semibold text-text-primary leading-tight">
              {username ?? 'User'}
            </p>
            <p className="text-xs text-text-muted capitalize">
              {role ?? 'Operator'}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={logout}
          className="inline-flex items-center px-space-3 py-space-2 text-xs font-semibold text-accent-danger bg-bg-surface border border-accent-danger rounded-radius-lg hover:bg-bg-surface hover:opacity-80 transition-opacity focus:ring-2 focus:ring-accent-primary"
          aria-label="Log out of application"
        >
          <LogOut className="w-3.5 h-3.5 mr-space-1" aria-hidden="true" />
          Log Out
        </button>
      </div>
    </header>
  );
};
