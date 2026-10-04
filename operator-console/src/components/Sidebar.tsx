import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Bell, FileText, Activity } from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navItems = [
    { to: '/', label: 'Live Monitor', icon: LayoutDashboard, exact: true },
    { to: '/alerts', label: 'Alert Center', icon: Bell },
    { to: '/reports', label: 'Reports', icon: FileText },
  ];

  return (
    <aside
      className="w-64 bg-bg-surface border-r border-border-subtle flex flex-col justify-between p-space-6 shadow-sm min-h-screen"
      aria-label="Main Navigation"
    >
      <div className="space-y-space-8">
        <div className="flex items-center space-x-space-3 px-space-2">
          <div className="w-8 h-8 rounded-radius-lg bg-accent-primary flex items-center justify-center text-bg-surface font-bold text-base">
            <Activity className="w-5 h-5 text-bg-surface" />
          </div>
          <div>
            <h1 className="text-base font-bold text-text-primary tracking-tight">
              ClassAware
            </h1>
            <span className="text-xs text-text-muted">Operator Console</span>
          </div>
        </div>

        <nav className="space-y-space-2" aria-label="Sidebar links">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.exact}
                className={({ isActive }) =>
                  `flex items-center space-x-space-3 px-space-4 py-space-3 rounded-radius-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-bg-info text-accent-primary font-semibold border-l-4 border-accent-primary'
                      : 'text-text-secondary hover:text-text-primary hover:bg-bg-info'
                  }`
                }
              >
                <Icon className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      <div className="pt-space-6 border-t border-border-subtle text-xs text-text-muted">
        <p className="font-semibold text-text-secondary">AI Monitoring System</p>
        <p>Inference: MobileViT + ViT</p>
      </div>
    </aside>
  );
};
