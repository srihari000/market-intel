import axios from 'axios';
import type { Run, Report } from '../types';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({ baseURL: BASE_URL });

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const authApi = {
  register: (email: string, password: string) =>
    api.post<{ access_token: string }>('/auth/register', { email, password }),
  login: (email: string, password: string) =>
    api.post<{ access_token: string }>('/auth/login', { email, password }),
  me: () => api.get<{ id: string; email: string }>('/auth/me'),
};

export const runsApi = {
  list: () => api.get<{ runs: Run[]; total: number }>('/runs'),
  create: (data: { title: string; competitors: string[]; topics: string[]; source_urls: string[] }) =>
    api.post<Run>('/runs', data),
  get: (id: string) => api.get<Run>(`/runs/${id}`),
  getReport: (id: string) => api.get<Report>(`/runs/${id}/report`),
  delete: (id: string) => api.delete(`/runs/${id}`),
  streamUrl: (id: string): string => {
    const token = sessionStorage.getItem('token') ?? '';
    return `${BASE_URL}/runs/${id}/stream?token=${encodeURIComponent(token)}`;
  },
};
