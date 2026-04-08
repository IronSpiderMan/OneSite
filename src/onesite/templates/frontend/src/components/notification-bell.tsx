import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Bell, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Modal } from './ui/modal';
import { features } from '../features';
import { formatDateTime, getUserTimeZone } from '../lib/datetime';
import {
  NotificationDetail,
  NotificationPreview,
  buildNotificationWsUrl,
  getInbox,
  getNotificationDetail,
  getUnreadCount,
  markAsRead,
  markAllRead,
} from '../services/notification-center';

export function NotificationBell({ onStatusChange }: { onStatusChange?: (online: boolean) => void }) {
  const { t } = useTranslation();
  const timeZone = getUserTimeZone();

  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [items, setItems] = useState<NotificationPreview[]>([]);
  const [unread, setUnread] = useState(0);

  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detail, setDetail] = useState<NotificationDetail | null>(null);
  const [markingAllRead, setMarkingAllRead] = useState(false);
  const recentlyReadIds = useRef<Set<number>>(new Set());

  const boxRef = useRef<HTMLDivElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const enabled = features.notifications.enabled;

  const loadUnread = async () => {
    if (!enabled) return;
    try {
      const r = await getUnreadCount();
      setUnread(r.unread || 0);
    } catch (e) {
      console.error(e);
    }
  };

  const loadPage = async (nextPage: number) => {
    if (!enabled) return;
    try {
      setLoading(true);
      const res = await getInbox(nextPage, 20);
      setHasMore(res.items.length > 0 && nextPage < res.total_pages);
      setPage(res.page);
      setItems((prev) => (nextPage === 1 ? res.items : [...prev, ...res.items]));
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const openDetail = async (id: number) => {
    setDetailOpen(true);
    setDetail(null);
    setDetailLoading(true);
    try {
      const d = await getNotificationDetail(id);
      setDetail(d);
      if (!d.is_read) {
        // Add to recentlyReadIds BEFORE awaiting to prevent race condition with WebSocket
        recentlyReadIds.current.add(id);
        setTimeout(() => {
          recentlyReadIds.current.delete(id);
        }, 1000);
        await markAsRead(id);
        setItems((prev) => prev.map((x) => (x.id === id ? { ...x, is_read: true } : x)));
        setUnread((u) => Math.max(0, u - 1));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleMarkAllRead = async () => {
    if (unread === 0) return;
    try {
      setMarkingAllRead(true);
      await markAllRead();
      setItems((prev) => prev.map((x) => ({ ...x, is_read: true })));
      setUnread(0);
    } catch (e) {
      console.error(e);
      toast.error(t('common.error', 'Error'));
    } finally {
      setMarkingAllRead(false);
    }
  };

  useEffect(() => {
    if (!enabled) return;
    loadUnread();
  }, [enabled]);

  useEffect(() => {
    if (!enabled) return;
    let ws: WebSocket | null = null;
    let retryCount = 0;
    let timeoutId: ReturnType<typeof setTimeout>;

    const connect = () => {
      const url = buildNotificationWsUrl();
      if (!url) return;

      try {
        ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          retryCount = 0;
          onStatusChange?.(true);
        };

        ws.onmessage = (ev) => {
          try {
            const payload = JSON.parse(ev.data || '{}');
            if (payload?.type === 'notification' && payload?.data) {
              const n = payload.data as NotificationPreview;
              setUnread((u) => u + 1);
              setItems((prev) => [n, ...prev]);
              toast.message(n.title || t('notifications.new', 'New notification'), {
                description: n.summary || '',
              });
            } else if (payload?.type === 'read' && payload?.id) {
              // Skip if we just handled this read locally to avoid double-decrement
              if (!recentlyReadIds.current.has(payload.id)) {
                setItems((prev) =>
                  prev.map((x) => (x.id === payload.id ? { ...x, is_read: true } : x))
                );
                setUnread((u) => Math.max(0, u - 1));
              }
            } else if (payload?.type === 'all_read') {
              setItems((prev) => prev.map((x) => ({ ...x, is_read: true })));
              setUnread(0);
            }
          } catch (e) {
            console.error(e);
          }
        };

        ws.onclose = (event) => {
          onStatusChange?.(false);
          const delay = Math.min(1000 * Math.pow(2, retryCount), 30000);
          timeoutId = setTimeout(() => {
            retryCount++;
            connect();
          }, delay);
        };

        ws.onerror = (err) => {
          ws?.close();
        };
      } catch (e) {
        console.error(e);
      }
    };

    connect();

    return () => {
      if (timeoutId) clearTimeout(timeoutId);
      if (ws) {
        ws.onclose = null; // Prevent retry on intentional close
        ws.close();
      }
      wsRef.current = null;
    };
  }, [enabled, t]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (!open) return;
      const target = e.target as Node;
      if (boxRef.current?.contains(target)) return;
      if (panelRef.current?.contains(target)) return;
      setOpen(false);
    };
    window.addEventListener('mousedown', onClick);
    return () => window.removeEventListener('mousedown', onClick);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    loadPage(1);
  }, [open]);

  const title = useMemo(() => t('notifications.title', 'Notifications'), [t]);

  if (!enabled) return null;

  return (
    <div className="relative" ref={boxRef}>
      <Button
        variant="ghost"
        size="icon"
        type="button"
        onClick={() => setOpen((v) => !v)}
        title={title}
        className="relative"
      >
        <Bell className="h-5 w-5" />
        {unread > 0 ? (
          <span className="absolute -right-1 -top-1">
            <Badge variant="destructive" className="h-5 px-1.5 text-[11px]">
              {unread > 99 ? '99+' : unread}
            </Badge>
          </span>
        ) : null}
      </Button>

      {open ? (
        <div
          ref={panelRef}
          className="absolute right-0 mt-2 w-[360px] max-w-[90vw] rounded-lg border bg-background shadow-lg z-50"
        >
          <Card className="border-0 shadow-none">
            <CardHeader className="py-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{title}</CardTitle>
                <div className="flex items-center gap-1">
                  {unread > 0 ? (
                    <Button variant="ghost" size="sm" type="button" onClick={handleMarkAllRead} disabled={markingAllRead}>
                      {markingAllRead ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                      {t('notifications.mark_all_read', 'Mark all read')}
                    </Button>
                  ) : null}
                  <Button variant="ghost" size="sm" type="button" onClick={loadUnread}>
                    {t('common.retry', 'Retry')}
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div
                className="max-h-[420px] overflow-auto"
                onScroll={(e) => {
                  const el = e.currentTarget;
                  if (loading || !hasMore) return;
                  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 24) {
                    loadPage(page + 1);
                  }
                }}
              >
                {items.length === 0 && !loading ? (
                  <div className="p-4 text-sm text-muted-foreground">
                    {t('notifications.empty', 'No notifications')}
                  </div>
                ) : (
                  <div className="divide-y">
                    {items.map((n) => (
                      <button
                        key={n.id}
                        type="button"
                        className="w-full text-left p-4 hover:bg-accent/50 transition-colors"
                        onClick={() => openDetail(n.id)}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              {!n.is_read ? (
                                <span className="h-2 w-2 rounded-full bg-primary mt-1" />
                              ) : null}
                              <div className="font-medium truncate">{n.title}</div>
                            </div>
                            <div className="mt-1 text-sm text-muted-foreground line-clamp-2">
                              {n.summary}
                            </div>
                          </div>
                          <div className="text-xs text-muted-foreground whitespace-nowrap">
                            {formatDateTime(n.created_at, timeZone)}
                          </div>
                        </div>
                      </button>
                    ))}
                    {loading ? (
                      <div className="p-4 flex items-center justify-center text-muted-foreground">
                        <Loader2 className="h-5 w-5 animate-spin" />
                      </div>
                    ) : null}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}

      <Modal
        title={t('notifications.detail', 'Notification')}
        isOpen={detailOpen}
        onClose={() => setDetailOpen(false)}
      >
        <div className="space-y-3">
          {detailLoading ? (
            <div className="flex items-center justify-center text-muted-foreground py-8">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : detail ? (
            <>
              <div className="text-lg font-semibold">{detail.title}</div>
              <div className="text-sm text-muted-foreground">{formatDateTime(detail.created_at, timeZone)}</div>
              <div className="whitespace-pre-wrap break-words rounded-md border bg-muted/30 p-3 text-sm">
                {detail.content}
              </div>
            </>
          ) : (
            <div className="text-sm text-muted-foreground">{t('common.error')}</div>
          )}
        </div>
      </Modal>
    </div>
  );
}

