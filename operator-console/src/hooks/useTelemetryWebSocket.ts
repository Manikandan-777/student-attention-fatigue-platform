import { useState, useEffect, useRef, useCallback } from 'react';
import { WS_TELEMETRY_URL } from '../config';
import { useAuthStore } from '../store/authStore';
import {
  ClassSnapshot,
  TrackResult,
  Alert,
  SystemStatus,
  TelemetryMessage,
  AlertMessage,
  SystemStatusMessage,
} from '../types';

interface UseTelemetryOptions {
  sessionId?: number | null;
}

export function useTelemetryWebSocket({ sessionId }: UseTelemetryOptions = {}) {
  const token = useAuthStore((state) => state.token);
  const [isConnected, setIsConnected] = useState(false);
  const [snapshot, setSnapshot] = useState<ClassSnapshot | null>(null);
  const [tracks, setTracks] = useState<TrackResult[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const connect = useCallback(() => {
    if (!token) return;

    const wsUrl = `${WS_TELEMETRY_URL}?token=${encodeURIComponent(token)}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      if (sessionId) {
        ws.send(JSON.stringify({ type: 'subscribe', session_id: sessionId }));
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'telemetry') {
          const msg = data as TelemetryMessage;
          setSnapshot(msg.snapshot);
          setTracks(msg.tracks);
        } else if (data.type === 'alert') {
          const msg = data as AlertMessage;
          setAlerts((prev) => {
            // Avoid duplicate alerts
            if (prev.some((a) => a.id === msg.alert.id)) {
              return prev.map((a) => (a.id === msg.alert.id ? msg.alert : a));
            }
            return [msg.alert, ...prev];
          });
        } else if (data.type === 'system_status') {
          const msg = data as SystemStatusMessage;
          setSystemStatus(msg.status);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      // Attempt reconnect after 3 seconds
      reconnectTimeoutRef.current = window.setTimeout(() => {
        connect();
      }, 3000);
    };

    ws.onerror = (err) => {
      console.warn('WebSocket connection error:', err);
      ws.close();
    };
  }, [token, sessionId]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  // Handle session change subscription
  useEffect(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && sessionId) {
      wsRef.current.send(JSON.stringify({ type: 'subscribe', session_id: sessionId }));
    }
  }, [sessionId]);

  return {
    isConnected,
    snapshot,
    tracks,
    alerts,
    setAlerts,
    systemStatus,
  };
}
