import { useEffect, useRef, useState, useCallback } from 'react';
import { WS_BASE_URL } from '../../config';
import { useAuthStore } from '../../store/authStore';
import { LiveTrackResult, LiveIncomingMsg } from './types';
import { getErrorMessage } from './errors';

interface UseLiveSocketOptions {
  enabled: boolean;
  onTrackUpdate?: (tracks: LiveTrackResult[]) => void;
}

export function useLiveSocket({
  enabled,
  onTrackUpdate,
}: UseLiveSocketOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [isSlowConnection, setIsSlowConnection] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [latestTracks, setLatestTracks] = useState<LiveTrackResult[]>([]);
  const [lastLatencyMs, setLastLatencyMs] = useState<number>(0);

  const socketRef = useRef<WebSocket | null>(null);
  const inFlightRef = useRef(false);
  const seqRef = useRef(1);
  const lastReplyTimeRef = useRef(Date.now());
  const pingIntervalRef = useRef<number | null>(null);
  const watchdogIntervalRef = useRef<number | null>(null);

  const sendFrame = useCallback((jpegB64: string) => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      return false;
    }
    if (inFlightRef.current) {
      return false; // Strict guarantee: Only one frame in flight at a time
    }

    inFlightRef.current = true;
    const currentSeq = seqRef.current++;

    socketRef.current.send(
      JSON.stringify({
        type: 'frame',
        seq: currentSeq,
        ts: new Date().toISOString(),
        jpeg_b64: jpegB64,
      })
    );
    return true;
  }, []);

  useEffect(() => {
    if (!enabled) {
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
      setIsConnected(false);
      setLatestTracks([]);
      inFlightRef.current = false;
      return;
    }

    const token = useAuthStore.getState().token;
    if (!token) {
      setErrorMessage(getErrorMessage('4403'));
      return;
    }

    // Determine correct WS protocol based on window.location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const base = WS_BASE_URL.startsWith('http') || WS_BASE_URL.startsWith('ws')
      ? WS_BASE_URL.replace(/^http/, 'ws')
      : `${protocol}//${host}`;

    const wsUrl = `${base}/ws/live-camera?token=${encodeURIComponent(token)}`;

    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;
    setErrorMessage(null);
    lastReplyTimeRef.current = Date.now();

    ws.onopen = () => {
      setIsConnected(true);
      setIsSlowConnection(false);

      // Heartbeat ping every 20s
      pingIntervalRef.current = window.setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 20000);

      // In-flight watchdog: unblock if response hangs > 3s
      watchdogIntervalRef.current = window.setInterval(() => {
        if (inFlightRef.current && Date.now() - lastReplyTimeRef.current > 3000) {
          inFlightRef.current = false;
          setIsSlowConnection(true);
        }
      }, 1000);
    };

    ws.onmessage = (event) => {
      try {
        const data: LiveIncomingMsg = JSON.parse(event.data);
        lastReplyTimeRef.current = Date.now();
        setIsSlowConnection(false);

        if (data.type === 'live_result') {
          inFlightRef.current = false;
          setLatestTracks(data.tracks);
          setLastLatencyMs(data.latency_ms);
          onTrackUpdate?.(data.tracks);
        } else if (data.type === 'skipped') {
          inFlightRef.current = false;
        } else if (data.type === 'error') {
          inFlightRef.current = false;
          if (data.code === 'bad_frame') {
            console.warn('Live camera bad frame:', data.message);
          }
        }
      } catch {
        inFlightRef.current = false;
      }
    };

    ws.onclose = (event) => {
      setIsConnected(false);
      inFlightRef.current = false;
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      if (watchdogIntervalRef.current) clearInterval(watchdogIntervalRef.current);

      if (event.code !== 1000 && event.code !== 1005) {
        setErrorMessage(getErrorMessage(String(event.code)));
      }
    };

    ws.onerror = () => {
      setIsConnected(false);
      inFlightRef.current = false;
    };

    return () => {
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      if (watchdogIntervalRef.current) clearInterval(watchdogIntervalRef.current);
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
      socketRef.current = null;
    };
  }, [enabled, onTrackUpdate]);

  return {
    isConnected,
    isSlowConnection,
    errorMessage,
    latestTracks,
    lastLatencyMs,
    sendFrame,
  };
}
