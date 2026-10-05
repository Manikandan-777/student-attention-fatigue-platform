export interface LiveTrackResult {
  track_id: number;
  label: string;
  bbox: [number, number, number, number]; // [x, y, w, h] normalized in [0, 1]
  bbox_normalized: boolean;
  warming_up: boolean;
  attention_status: 'Attentive' | 'Distracted' | 'Unknown';
  fatigue_status: 'Normal' | 'Fatigued' | 'Unknown';
  attention_score: number;
  fatigue_index: number;
  confidence: number;
  expression: { top: string; confidence: number } | null;
}

export interface LiveResultMsg {
  type: 'live_result';
  seq?: number;
  ts: string;
  frame_size: [number, number];
  latency_ms: number;
  model_mode: string;
  tracks: LiveTrackResult[];
}

export interface LiveSkippedMsg {
  type: 'skipped';
  seq?: number;
  reason: string;
}

export interface LiveErrorMsg {
  type: 'error';
  code: string;
  message: string;
}

export type LiveIncomingMsg = LiveResultMsg | LiveSkippedMsg | LiveErrorMsg | { type: 'pong' };
