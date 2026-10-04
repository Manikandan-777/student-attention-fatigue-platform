import React from 'react';
import { AlertCircle, CheckCircle2, Eye, Bell } from 'lucide-react';
import { Alert, AlertStatus } from '../types';
import { StatusBadge } from './StatusBadge';

interface AlertItemProps {
  alert: Alert;
  onUpdateStatus: (alertId: number, nextStatus: AlertStatus) => Promise<void>;
  isUpdating?: boolean;
}

export const AlertItem: React.FC<AlertItemProps> = ({
  alert,
  onUpdateStatus,
  isUpdating = false,
}) => {
  const formatTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoString;
    }
  };

  const getAlertIcon = () => {
    switch (alert.type) {
      case 'fatigue':
        return <AlertCircle className="w-5 h-5 text-accent-danger flex-shrink-0" aria-hidden="true" />;
      case 'distraction':
        return <Eye className="w-5 h-5 text-accent-primary flex-shrink-0" aria-hidden="true" />;
      case 'camera_offline':
      case 'ai_offline':
      default:
        return <Bell className="w-5 h-5 text-accent-danger flex-shrink-0" aria-hidden="true" />;
    }
  };

  return (
    <div
      tabIndex={0}
      className="bg-bg-surface border border-border-subtle rounded-radius-xl p-space-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-space-4 hover:border-border-strong transition-colors focus:ring-2 focus:ring-accent-primary focus:outline-none"
      aria-label={`Alert: ${alert.message}. Student: ${alert.label ?? 'System'}, Status: ${alert.status}`}
    >
      <div className="flex items-start space-x-space-4">
        {getAlertIcon()}
        <div>
          <div className="flex flex-wrap items-center gap-space-2 mb-space-1">
            <span className="text-text-primary text-sm font-bold">
              {alert.label ? `Student ${alert.label}` : 'System Alert'}
            </span>
            <span className="text-xs uppercase px-space-2 py-space-1 rounded-radius-md font-semibold bg-bg-info text-accent-primary border border-border-subtle">
              {alert.type.replace('_', ' ')}
            </span>
            <StatusBadge
              status={
                alert.status === 'Resolved'
                  ? 'Attentive'
                  : alert.status === 'Viewed'
                  ? 'Distracted'
                  : 'Fatigued'
              }
              size="sm"
            />
          </div>

          <p className="text-text-body text-sm mb-space-2 font-normal">
            {alert.message}
          </p>

          <div className="flex items-center space-x-space-4 text-xs text-text-muted">
            <span>Time: {formatTime(alert.created_at)}</span>
            <span>Confidence: {Math.round(alert.confidence * 100)}%</span>
            {alert.session_id && <span>Session #{alert.session_id}</span>}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-space-2 self-end md:self-center">
        {alert.status === 'New' && (
          <button
            type="button"
            disabled={isUpdating}
            onClick={() => onUpdateStatus(alert.id, 'Viewed')}
            className="inline-flex items-center px-space-3 py-space-2 text-xs font-semibold text-text-body bg-bg-surface border border-border-strong rounded-radius-lg hover:bg-bg-info focus:ring-2 focus:ring-accent-primary disabled:opacity-50 transition-colors"
            aria-label={`Mark alert ${alert.id} as Viewed`}
          >
            <Eye className="w-3.5 h-3.5 mr-space-1" aria-hidden="true" />
            Mark Viewed
          </button>
        )}

        {alert.status !== 'Resolved' && (
          <button
            type="button"
            disabled={isUpdating}
            onClick={() => onUpdateStatus(alert.id, 'Resolved')}
            className="inline-flex items-center px-space-3 py-space-2 text-xs font-semibold text-accent-success bg-bg-success border border-accent-success rounded-radius-lg hover:opacity-90 focus:ring-2 focus:ring-accent-primary disabled:opacity-50 transition-colors"
            aria-label={`Resolve alert ${alert.id}`}
          >
            <CheckCircle2 className="w-3.5 h-3.5 mr-space-1" aria-hidden="true" />
            Resolve
          </button>
        )}

        {alert.status === 'Resolved' && (
          <span className="text-xs text-accent-success font-semibold px-space-3 py-space-1 bg-bg-success border border-accent-success rounded-radius-pill">
            Resolved
          </span>
        )}
      </div>
    </div>
  );
};
