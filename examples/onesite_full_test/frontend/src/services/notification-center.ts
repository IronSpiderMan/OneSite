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

export const markAllRead = async () => {
  const base = features.notifications.apiBase;
  const response = await request.put<{ updated: number }>(`${base}/mark_all_read`, {});
  return response.data;
};

export const getNotificationDetail = async (id: number) => {
  const base = features.notifications.apiBase;
  const response = await request.get<NotificationDetail>(`${base}/${id}`);
  return response.data;
};

export function buildNotificationWsUrl(): string | null {
  const token = localStorage.getItem('token');
  if (!token) return null;

  // Always build WS URL if user is authenticated
  // The connection is used for both online status and notifications
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/api/v1/ws?token=${encodeURIComponent(token)}`;
}
