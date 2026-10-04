// Core Domain Types per contracts.md

export type AttentionStatus = 'Attentive' | 'Distracted' | 'Unknown';
export type FatigueStatus = 'Normal' | 'Fatigued' | 'Unknown';
export type AlertType = 'fatigue' | 'distraction' | 'camera_offline' | 'ai_offline';
export type AlertStatus = 'New' | 'Viewed' | 'Resolved';
export type ServiceState = 'Online' | 'Offline' | 'Degraded';
export type UserRole = 'teacher' | 'admin';

export interface TrackResult {
  track_id: number;
  label: string;
  bbox: [number, number, number, number];
  bbox_normalized: boolean;
  landmark_confidence: number;
  attention_score: number;
  fatigue_index: number;
  attention_status: AttentionStatus;
  fatigue_status: FatigueStatus;
  confidence: number;
  model_mode: 'heuristic' | 'lstm';
}

export interface ClassSnapshot {
  session_id: number;
  class_name: string;
  status: string;
  students_detected: number;
  counts: {
    attentive: number;
    distracted: number;
    unknown: number;
    fatigued: number;
  };
  avg_attention_score: number;
  open_alerts: number;
}

export interface Alert {
  id: number;
  session_id: number | null;
  track_id: number | null;
  label: string | null;
  type: AlertType;
  status: AlertStatus;
  message: string;
  confidence: number;
  created_at: string;
  viewed_at: string | null;
  resolved_at: string | null;
}

export interface SystemStatus {
  ai_server: ServiceState;
  database: ServiceState;
  api: ServiceState;
  cameras: Array<{ id: string; state: ServiceState }>;
  fps: number;
  model_mode: 'heuristic' | 'lstm';
  privacy_mode: boolean;
}

export interface SessionReportPerStudent {
  label: string;
  attention_mean: number;
  fatigue_index_mean: number;
  fatigue_indicators: number;
  distraction_indicators: number;
  alerts: number;
}

export interface SessionReport {
  session_id: number;
  class_name: string;
  date: string;
  start: string;
  end: string;
  duration_min: number;
  students: number;
  attention: {
    attentive: number;
    distracted: number;
    unknown: number;
  };
  fatigue: {
    normal: number;
    fatigued: number;
  };
  alerts_total: number;
  avg_attention_score: number;
  per_student: SessionReportPerStudent[];
}

export interface TelemetryMessage {
  type: 'telemetry';
  session_id: number;
  ts: string;
  snapshot: ClassSnapshot;
  tracks: TrackResult[];
}

export interface AlertMessage {
  type: 'alert';
  alert: Alert;
}

export interface SystemStatusMessage {
  type: 'system_status';
  status: SystemStatus;
}

export interface VideoFrameMessage {
  type: 'frame';
  session_id: number;
  ts: string;
  jpeg_b64: string;
  tracks: Array<{
    track_id: number;
    bbox: [number, number, number, number];
    attention_status: AttentionStatus;
    fatigue_status: FatigueStatus;
  }>;
}
