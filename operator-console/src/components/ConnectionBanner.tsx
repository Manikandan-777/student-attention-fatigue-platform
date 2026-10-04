import React from 'react';
import { AlertCircle, WifiOff } from 'lucide-react';

interface ConnectionBannerProps {
  isWsConnected: boolean;
  aiOffline?: boolean;
  cameraOffline?: boolean;
}

export const ConnectionBanner: React.FC<ConnectionBannerProps> = ({
  isWsConnected,
  aiOffline = false,
  cameraOffline = false,
}) => {
  if (isWsConnected && !aiOffline && !cameraOffline) {
    return null;
  }

  let message = '';
  if (!isWsConnected) {
    message = 'Disconnected from telemetry server. Attempting to reconnect...';
  } else if (aiOffline) {
    message = 'AI inference service is currently offline. Status indicators may be delayed.';
  } else if (cameraOffline) {
    message = 'Camera feed is unavailable or offline.';
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className="bg-bg-surface border border-accent-danger text-accent-danger p-space-4 rounded-radius-lg mb-space-6 flex items-center justify-between shadow-sm"
    >
      <div className="flex items-center space-x-space-4">
        {!isWsConnected ? (
          <WifiOff className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
        ) : (
          <AlertCircle className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
        )}
        <span className="text-sm font-medium">{message}</span>
      </div>
      <span className="text-xs uppercase font-bold tracking-wider px-space-2 py-space-1 border border-accent-danger rounded-radius-md">
        Offline Alert
      </span>
    </div>
  );
};
