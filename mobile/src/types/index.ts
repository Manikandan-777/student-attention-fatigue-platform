// Domain Types for Mobile Application

export type AttentionStatus = 'Attentive' | 'Distracted' | 'Unknown';
export type FatigueStatus = 'Normal' | 'Fatigued' | 'Unknown';
export type AlertType = 'fatigue' | 'distraction' | 'camera_offline' | 'ai_offline';
export type AlertStatus = 'New' | 'Viewed' | 'Resolved';
export type ServiceState = 'Online' | 'Offline' | 'Degraded';
export type UserRole = 'teacher' | 'admin';

// TrackResult-lite per contracts.md §4 (no landmarks, no probabilities)
export interface TrackResultLite {
  track_id: number;
  label: string;
  attention_status: AttentionStatus;
  fatigue_status: FatigueStatus;
  attention_score: number;
  confidence: number;
}

export interface FatigueAdvisory {
  class_fatigue_pct: number;
  level: 1 | 2 | 3 | 4;
  code: 'CONTINUE' | 'INTERACTIVE' | 'SHORT_BREAK' | 'RESCHEDULE';
  message: string;
  usable_tracks: number;
  since: string;
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
  fatigue_advisory?: FatigueAdvisory | null;
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

export interface Student {
  id: number;
  student_id: string;
  name: string;
  department: string;
  year: number;
  section: string;
  is_active: boolean;
}

export interface Teacher {
  id: number;
  user_id: number;
  name: string;
  email: string;
  department: string;
  is_active: boolean;
}

export interface Classroom {
  id: number;
  name: string;
  camera_id: string;
  is_active: boolean;
}

export interface Session {
  id: number;
  classroom_id: number;
  teacher_id: number;
  status: 'Scheduled' | 'Monitoring' | 'Completed' | 'Aborted';
  started_at: string | null;
  ended_at: string | null;
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
