import axios, { AxiosInstance } from 'axios';
import { API_BASE_URL } from '../config';
import { StorageService } from './storage';
import {
  ClassSnapshot,
  Classroom,
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
    return res.data as { id: number; username: string; role: string; active: boolean };
  },

  async logout() {
    try {
      await apiClient.post('/auth/logout');
    } catch {
      // Ignore network errors on logout
    }
  },

  async getTeacherDashboard(): Promise<ClassSnapshot | null> {
    const res = await apiClient.get<ClassSnapshot | ClassSnapshot[]>('/teacher/dashboard');
    if (Array.isArray(res.data)) {
      return res.data.length > 0 ? res.data[0] : null;
    }
    return res.data ?? null;
  },

  async getSessions(): Promise<Session[]> {
    const res = await apiClient.get<Session[]>('/sessions');
    return res.data;
  },

  async getClassrooms(): Promise<Classroom[]> {
    const res = await apiClient.get<Classroom[]>('/classrooms');
    return res.data;
  },

  // Admin CRUD for Teachers (§7)
  async getTeachers(): Promise<Teacher[]> {
    const res = await apiClient.get<Teacher[]>('/teachers');
    return res.data;
  },

  async createTeacher(data: {
    username: string;
    password: string;
    display_name: string;
    classroom_id?: number;
    active?: boolean;
  }): Promise<Teacher> {
    const res = await apiClient.post<Teacher>('/teachers', data);
    return res.data;
  },

  async updateTeacher(
    teacherId: number,
    data: {
      display_name?: string;
      active?: boolean;
      classroom_id?: number;
    }
  ): Promise<Teacher> {
    const res = await apiClient.put<Teacher>(`/teachers/${teacherId}`, data);
    return res.data;
  },

  async deleteTeacher(teacherId: number): Promise<void> {
    await apiClient.delete(`/teachers/${teacherId}`);
  },

  async assignTeacherClassroom(teacherId: number, classroomId: number): Promise<void> {
    await apiClient.post(`/teachers/${teacherId}/assign-classroom`, null, {
      params: { classroom_id: classroomId },
    });
  },
};
