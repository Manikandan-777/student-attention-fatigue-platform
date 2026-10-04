import axios, { AxiosInstance } from 'axios';
import { API_BASE_URL } from '../config';
import { StorageService } from './storage';
import {
  ClassSnapshot,
  Alert,
  AlertStatus,
  SessionReport,
  SystemStatus,
  Classroom,
  Student,
  Teacher,
  Session,
} from '../types';

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(async (config) => {
  const token = await StorageService.getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const ApiService = {
  async login(username: string, password: string) {
    const res = await apiClient.post('/auth/login', { username, password });
    return res.data as { access_token: string; role: string; token_type: string };
  },

  async getMe() {
    const res = await apiClient.get('/auth/me');
    return res.data as { id: number; username: string; role: string };
  },

  async getTeacherDashboard() {
    const res = await apiClient.get<ClassSnapshot>('/teacher/dashboard');
    return res.data;
  },

  async getClassrooms() {
    const res = await apiClient.get<Classroom[]>('/classrooms');
    return res.data;
  },

  async getClassroomStudents(classroomId: number) {
    const res = await apiClient.get<Student[]>(`/classrooms/${classroomId}/students`);
    return res.data;
  },

  async getSessions() {
    const res = await apiClient.get<Session[]>('/sessions');
    return res.data;
  },

  async startSession(classroomId: number) {
    const res = await apiClient.post<Session>('/sessions', { classroom_id: classroomId });
    return res.data;
  },

  async stopSession(sessionId: number) {
    const res = await apiClient.post<Session>(`/sessions/${sessionId}/stop`);
    return res.data;
  },

  async getAlerts(status?: string, sessionId?: number) {
    const params: Record<string, unknown> = {};
    if (status) params.status = status;
    if (sessionId) params.session_id = sessionId;
    const res = await apiClient.get<Alert[]>('/alerts', { params });
    return res.data;
  },

  async updateAlertStatus(alertId: number, nextStatus: AlertStatus) {
    const res = await apiClient.patch<Alert>(`/alerts/${alertId}`, {
      status: nextStatus,
    });
    return res.data;
  },

  async getReports() {
    const res = await apiClient.get<SessionReport[]>('/reports');
    return res.data;
  },

  async getReport(sessionId: number) {
    const res = await apiClient.get<SessionReport>(`/reports/${sessionId}`);
    return res.data;
  },

  async getSystemStatus() {
    const res = await apiClient.get<SystemStatus>('/system/status');
    return res.data;
  },

  // Admin CRUD
  async getStudents() {
    const res = await apiClient.get<Student[]>('/students');
    return res.data;
  },

  async createStudent(data: Partial<Student>) {
    const res = await apiClient.post<Student>('/students', data);
    return res.data;
  },

  async deactivateStudent(id: number) {
    const res = await apiClient.delete(`/students/${id}`);
    return res.data;
  },

  async getTeachers() {
    const res = await apiClient.get<Teacher[]>('/teachers');
    return res.data;
  },

  async createTeacher(data: Partial<Teacher>) {
    const res = await apiClient.post<Teacher>('/teachers', data);
    return res.data;
  },

  async assignTeacherClassroom(teacherId: number, classroomId: number) {
    const res = await apiClient.post(`/teachers/${teacherId}/assign`, {
      classroom_id: classroomId,
    });
    return res.data;
  },
};
