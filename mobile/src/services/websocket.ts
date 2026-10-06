import { WS_TELEMETRY_URL } from '../config';
import { StorageService } from './storage';
import { Alert, ClassSnapshot, TrackResultLite } from '../types';

export type TelemetryListener = (data: {
  snapshot?: ClassSnapshot;
  tracks?: TrackResultLite[];
  ts?: string;
}) => void;

export type AlertListener = (alert: Alert) => void;
export type ConnectionListener = (isConnected: boolean) => void;

export class MobileTelemetryClient {
  private ws: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private isDestroyed = false;
  private currentSessionId?: number;

  private telemetryListeners: Set<TelemetryListener> = new Set();
  private alertListeners: Set<AlertListener> = new Set();
  private connectionListeners: Set<ConnectionListener> = new Set();

  async connect(sessionId?: number): Promise<void> {
    this.isDestroyed = false;
    this.currentSessionId = sessionId;
    const token = await StorageService.getToken();
    if (!token) return;

    const url = `${WS_TELEMETRY_URL}?token=${encodeURIComponent(token)}`;

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this.notifyConnection(true);
        if (this.currentSessionId && this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'subscribe', session_id: this.currentSessionId }));
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'telemetry') {
            this.telemetryListeners.forEach((l) =>
              l({ snapshot: msg.snapshot, tracks: msg.tracks, ts: msg.ts })
            );
          } else if (msg.type === 'alert' && msg.alert) {
            this.alertListeners.forEach((l) => l(msg.alert));
          }
        } catch (e) {
          console.warn('Failed to parse WebSocket message:', e);
        }
      };

      this.ws.onclose = () => {
        this.notifyConnection(false);
        this.scheduleReconnect();
      };

      this.ws.onerror = () => {
        this.notifyConnection(false);
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.close();
        }
      };
    } catch {
      this.notifyConnection(false);
      this.scheduleReconnect();
    }
  }

  subscribeSession(sessionId: number): void {
    this.currentSessionId = sessionId;
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'subscribe', session_id: sessionId }));
    }
  }

  private notifyConnection(connected: boolean) {
    this.connectionListeners.forEach((l) => l(connected));
  }

  private scheduleReconnect() {
    if (this.isDestroyed) return;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => {
      this.connect(this.currentSessionId);
    }, 4000);
  }

  onTelemetry(listener: TelemetryListener): () => void {
    this.telemetryListeners.add(listener);
    return () => this.telemetryListeners.delete(listener);
  }

  onAlert(listener: AlertListener): () => void {
    this.alertListeners.add(listener);
    return () => this.alertListeners.delete(listener);
  }

  onConnectionChange(listener: ConnectionListener): () => void {
    this.connectionListeners.add(listener);
    return () => this.connectionListeners.delete(listener);
  }

  disconnect(): void {
    this.isDestroyed = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.notifyConnection(false);
  }
}

export const mobileTelemetry = new MobileTelemetryClient();
export const WebSocketService = mobileTelemetry;
