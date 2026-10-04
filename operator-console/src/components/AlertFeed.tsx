import React, { useState, useMemo } from 'react';
import { Bell, Filter, CheckCircle2 } from 'lucide-react';
import { Alert, AlertStatus } from '../types';
import { AlertItem } from './AlertItem';

interface AlertFeedProps {
  alerts: Alert[];
  onUpdateStatus: (alertId: number, nextStatus: AlertStatus) => Promise<void>;
  isLoading?: boolean;
}

export const AlertFeed: React.FC<AlertFeedProps> = ({
  alerts,
  onUpdateStatus,
  isLoading = false,
}) => {
  const [statusFilter, setStatusFilter] = useState<'All' | AlertStatus>('All');
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  // Newest first sorting (reverse chronological)
  const sortedAndFilteredAlerts = useMemo(() => {
    return alerts
      .filter((a) => (statusFilter === 'All' ? true : a.status === statusFilter))
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [alerts, statusFilter]);

  const handleUpdate = async (id: number, status: AlertStatus) => {
    setUpdatingId(id);
    try {
      await onUpdateStatus(id, status);
    } finally {
      setUpdatingId(null);
    }
  };

  const filterButtons: Array<'All' | AlertStatus> = ['All', 'New', 'Viewed', 'Resolved'];

  return (
    <div className="space-y-space-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-4">
        <div className="flex items-center space-x-space-4">
          <Bell className="w-5 h-5 text-accent-danger" aria-hidden="true" />
          <h2 className="text-lg font-bold text-text-primary">
            Alert Center & Event Feed
          </h2>
          <span className="text-xs bg-bg-info text-accent-primary font-semibold px-space-3 py-space-1 rounded-radius-pill border border-accent-primary">
            {sortedAndFilteredAlerts.length} shown
          </span>
        </div>

        {/* Status filters */}
        <div
          role="group"
          aria-label="Filter alerts by status"
          className="flex items-center space-x-space-1 bg-bg-surface border border-border-subtle p-space-1 rounded-radius-lg"
        >
          <Filter className="w-3.5 h-3.5 text-text-secondary ml-space-2 mr-space-1" aria-hidden="true" />
          {filterButtons.map((btn) => (
            <button
              key={btn}
              type="button"
              onClick={() => setStatusFilter(btn)}
              className={`px-space-3 py-space-1 text-xs font-semibold rounded-radius-md transition-colors ${
                statusFilter === btn
                  ? 'bg-accent-primary text-bg-surface shadow-sm'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-info'
              }`}
              aria-pressed={statusFilter === btn}
            >
              {btn}
            </button>
          ))}
        </div>
      </div>

      {/* Live notification region */}
      <div
        role="region"
        aria-live="polite"
        aria-label="Live alert updates"
        className="space-y-space-4"
      >
        {isLoading && alerts.length === 0 ? (
          <div className="bg-bg-surface border border-border-subtle rounded-radius-xl p-space-12 text-center shadow-sm text-text-muted">
            Loading alerts...
          </div>
        ) : sortedAndFilteredAlerts.length === 0 ? (
          <div className="bg-bg-surface border border-border-subtle rounded-radius-xl p-space-12 text-center shadow-sm">
            <CheckCircle2 className="w-10 h-10 text-accent-success mx-auto mb-space-4" aria-hidden="true" />
            <h3 className="text-base font-semibold text-text-primary mb-space-1">
              No alerts found
            </h3>
            <p className="text-sm text-text-secondary">
              {statusFilter === 'All'
                ? 'All quiet! No open or past alerts reported for this session.'
                : `No alerts currently with status "${statusFilter}".`}
            </p>
          </div>
        ) : (
          sortedAndFilteredAlerts.map((alert) => (
            <AlertItem
              key={alert.id}
              alert={alert}
              isUpdating={updatingId === alert.id}
              onUpdateStatus={handleUpdate}
            />
          ))
        )}
      </div>
    </div>
  );
};
