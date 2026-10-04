import { WS_TELEMETRY_URL } from '../config';
import { StorageService } from './storage';
import { ClassSnapshot, TrackResultLite, Alert, SystemStatus } from '../types';

export type TelemetryListener = (data: {
  snapshot?: ClassSnapshot;
  tracks?: TrackResultLite[];
}) => void;

export type AlertListener = (alert: Alert) => void;
export type SystemStatusListener = (status: SystemStatus) => void;
export type ConnectionListener = (isConnected: boolean) => void;

export class MobileTelemetryClient {
  private ws: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private isDestroyed = false;

  private telemetryListeners: Set<TelemetryListener> = new Set();
  private alertListeners: Set<AlertListener> = new Set();
  private systemStatusListeners: Set<SystemStatusListener> = new Set();
  private connectionListeners: Set<ConnectionListener> = new Set();

  async connect(sessionId?: number): Promise<void> {
    this.isDestroyed = false;
    const token = await StorageService.getToken();
    if (!token) return;

    const url = `${WS_TELEMETRY_URL}?token=${encodeURIComponent(token)}`;

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this.notifyConnection(true);
        if (sessionId && this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'subscribe', session_id: sessionId }));
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'telemetry') {
            this.telemetryListeners.forEach((l) =>
              l({ snapshot: msg.snapshot, tracks: msg.tracks })
            );
          } else if (msg.type === 'alert') {
            this.alertListeners.forEach((l) => l(msg.alert));
          } else if (msg.type === 'system_status') {
            this.systemStatusListeners.forEach((l) => l(msg.status));
          }
        } catch (e) {
          console.warn('Failed to parse WebSocket message:', e);
        }
      };

      this.ws.onclose = () => {
        this.notifyConnection(false);
        this.scheduleReconnect(sessionId);
      };

      this.ws.onerror = () => {
        this.notifyConnection(false);
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.close();
        }
      };
    } catch {
      this.notifyConnection(false);
      this.scheduleReconnect(sessionId);
    }
  }

  private notifyConnection(connected: boolean) {
    this.connectionListeners.forEach((l) => l(connected));
  }

  private scheduleReconnect(sessionId?: number) {
    if (this.isDestroyed) return;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => {
      this.connect(sessionId);
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

  onSystemStatus(listener: SystemStatusListener): () => void {
    this.systemStatusListeners.add(listener);
    return () => this.systemStatusListeners.delete(listener);
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
