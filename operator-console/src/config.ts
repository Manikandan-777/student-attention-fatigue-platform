// API and WebSocket base URLs
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL ?? 'ws://localhost:8000';

export const WS_TELEMETRY_URL = `${WS_BASE_URL}/ws/telemetry`;
export const WS_VIDEO_URL = `${WS_BASE_URL}/ws/video`;

export const TELEMETRY_HZ = 2; // frames per second for telemetry updates
