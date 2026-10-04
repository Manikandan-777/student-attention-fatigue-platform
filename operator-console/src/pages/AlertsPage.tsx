import React, { useEffect, useState } from 'react';
import apiClient from '../api/client';
import { Alert, AlertStatus } from '../types';
import { useTelemetryWebSocket } from '../hooks/useTelemetryWebSocket';
import { AlertFeed } from '../components/AlertFeed';

export const AlertsPage: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { alerts: wsAlerts } = useTelemetryWebSocket();

  // Load initial alerts from REST API
  useEffect(() => {
    const fetchAlerts = async () => {
      setIsLoading(true);
      setErrorMsg(null);
      try {
        const response = await apiClient.get<Alert[]>('/alerts');
        setAlerts(response.data);
      } catch (err: unknown) {
        console.error('Failed to fetch alerts:', err);
        setErrorMsg('Unable to retrieve alerts from server.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchAlerts();
  }, []);

  // Merge any incoming WebSocket alerts
  useEffect(() => {
    if (wsAlerts.length > 0) {
      setAlerts((prev) => {
        const existingIds = new Set(prev.map((a) => a.id));
        const newOnes = wsAlerts.filter((a) => !existingIds.has(a.id));
        return [...newOnes, ...prev];
      });
    }
  }, [wsAlerts]);

  const handleUpdateStatus = async (alertId: number, nextStatus: AlertStatus) => {
    try {
      const response = await apiClient.patch<Alert>(`/alerts/${alertId}`, {
        status: nextStatus,
      });

      // Update in state
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? response.data : a))
      );
    } catch (err) {
      console.error(`Failed to update alert ${alertId} status:`, err);
    }
  };

  return (
    <div className="space-y-space-6">
      {errorMsg && (
        <div
          role="alert"
          className="bg-bg-surface border border-accent-danger text-accent-danger p-space-4 rounded-radius-lg text-sm shadow-sm"
        >
          {errorMsg}
        </div>
      )}

      <AlertFeed
        alerts={alerts}
        onUpdateStatus={handleUpdateStatus}
        isLoading={isLoading}
      />
    </div>
  );
};
