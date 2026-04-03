import request from '../utils/request';
import { features } from '../features';

export type NotificationPreview = {
  id: number;
  title: string;
  summary: string;
  created_at: string;
  is_read: boolean;
};

export type NotificationDetail = NotificationPreview & {
  content: string;
};

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  total_pages: number;
}

export const getInbox = async (page = 1, size = 20) => {
  const base = features.notifications.apiBase;
  const response = await request.get<PaginatedResponse<NotificationPreview>>(
    `${base}/inbox?page=${page}&size=${size}`
  );
  return response.data;
};

export const getUnreadCount = async () => {
  const base = features.notifications.apiBase;
  const response = await request.get<{ unread: number }>(`${base}/unread_count`);
  return response.data;
};

export const markAsRead = async (id: number) => {
  const base = features.notifications.apiBase;
  const response = await request.put(`${base}/${id}/read`, {});
  return response.data;
};

export const getNotificationDetail = async (id: number) => {
  const base = features.notifications.apiBase;
  const response = await request.get<NotificationDetail>(`${base}/${id}`);
  return response.data;
};

export function buildNotificationWsUrl(): string | null {
  if (!features.notifications.enabled) return null;
  const token = localStorage.getItem('token');
  if (!token) return null;
  const apiPrefix = (import.meta as any).env?.VITE_API_URL || '/api/v1';
  let origin = window.location.origin;
  let prefixPath = String(apiPrefix || '/api/v1');

  if (/^https?:\/\//i.test(prefixPath)) {
    const u = new URL(prefixPath);
    origin = u.origin;
    prefixPath = u.pathname;
  }

  prefixPath = prefixPath.replace(/\/$/, '');
  const wsOrigin = origin.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:');
  return `${wsOrigin}${prefixPath}/ws?token=${encodeURIComponent(token)}`;
}
