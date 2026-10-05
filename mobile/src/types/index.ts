// Minimal Domain Types for Mobile Application (§1-7)

export type AttentionStatus = 'Attentive' | 'Distracted' | 'Unknown';
export type FatigueStatus = 'Normal' | 'Fatigued' | 'Unknown';
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
  class_fatigue_pct?: number | null;
  open_alerts: number;
  fatigue_advisory?: FatigueAdvisory | null;
}

export interface Teacher {
  id: number;
  user_id: number;
  display_name: string;
  username: string;
  active: boolean;
  classroom_name?: string | null;
  classroom_id?: number | null;
}

export interface Classroom {
  id: number;
  room_name: string;
  class_name: string;
  camera_id?: string | null;
  active: boolean;
}

export interface Session {
  id: number;
  classroom_id: number;
  status: 'Scheduled' | 'Monitoring' | 'Completed' | 'Aborted';
  started_at: string;
  ended_at?: string | null;
  students_detected_max: number;
  class_name?: string | null;
  room_name?: string | null;
}

export interface TrendPoint {
  ts: string;
  value: number;
}
