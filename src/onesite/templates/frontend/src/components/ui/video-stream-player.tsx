import React, { useEffect, useMemo, useRef, useState } from 'react';
import Hls, { ErrorTypes } from 'hls.js';
import { AlertCircle, Loader2, RefreshCw, VideoOff } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from './button';
import { cn } from '../../lib/utils';
import request from '../../utils/request';

export type VideoStreamProtocol = 'auto' | 'native' | 'hls' | 'rtsp';
export type DetectedVideoStreamType =
    | 'hls'
    | 'native'
    | 'rtsp'
    | 'rtmp'
    | 'srt'
    | 'unknown';

const NATIVE_VIDEO_EXTENSIONS = /\.(mp4|webm|ogv|ogg|m4v|mov)$/i;

export function detectVideoStreamType(
    rawUrl: string,
    configured: VideoStreamProtocol = 'auto',
): DetectedVideoStreamType {
    if (configured !== 'auto') return configured;
    if (!rawUrl.trim()) return 'unknown';

    try {
        const url = new URL(rawUrl, window.location.origin);
        const scheme = url.protocol.toLowerCase();
        const pathname = url.pathname.toLowerCase();

        if (scheme === 'rtsp:' || scheme === 'rtsps:') return 'rtsp';
        if (scheme === 'rtmp:' || scheme === 'rtmps:') return 'rtmp';
        if (scheme === 'srt:') return 'srt';
        if (pathname.endsWith('.m3u8')) return 'hls';
        if (NATIVE_VIDEO_EXTENSIONS.test(pathname)) return 'native';
    } catch {
        return 'unknown';
    }

    return 'unknown';
}

export function resolveVideoStreamUrl(rawUrl: string): string {
    if (/^(https?:|blob:|data:)/i.test(rawUrl)) return rawUrl;

    const apiUrl = import.meta.env.VITE_API_URL;
    if (apiUrl && rawUrl.startsWith('/')) {
        return `${apiUrl.replace(/\/api\/v1\/?$/, '')}${rawUrl}`;
    }
    return rawUrl;
}

interface VideoStreamPlayerProps {
    src?: string | null;
    protocol?: VideoStreamProtocol;
    poster?: string;
    autoPlay?: boolean;
    muted?: boolean;
    controls?: boolean;
    reconnect?: boolean;
    className?: string;
}

export const VideoStreamPlayer: React.FC<VideoStreamPlayerProps> = ({
    src,
    protocol = 'auto',
    poster,
    autoPlay = false,
    muted = true,
    controls = true,
    reconnect = true,
    className,
}) => {
    const { t } = useTranslation();
    const videoRef = useRef<HTMLVideoElement>(null);
    const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
    const [errorKey, setErrorKey] = useState<string | null>(null);
    const [retryVersion, setRetryVersion] = useState(0);
    const [resolvedRtspSource, setResolvedRtspSource] = useState<string | null>(null);
    const streamType = useMemo(
        () => detectVideoStreamType(src || '', protocol),
        [src, protocol],
    );
    const playbackSource = streamType === 'rtsp' ? resolvedRtspSource : src;
    const playableType = streamType === 'rtsp' && resolvedRtspSource
        ? 'hls'
        : streamType === 'unknown'
          ? 'native'
          : streamType;

    useEffect(() => {
        let disposed = false;
        if (streamType !== 'rtsp' || !src?.trim()) {
            setResolvedRtspSource(null);
            return;
        }

        setStatus('loading');
        setErrorKey(null);
        setResolvedRtspSource(null);
        request.post('/video-streams/preview', { source_url: src.trim() })
            .then((response) => {
                if (!disposed) setResolvedRtspSource(response.data.hls_url);
            })
            .catch(() => {
                if (!disposed) {
                    setStatus('error');
                    setErrorKey('video_stream.rtsp_gateway_error');
                }
            });

        return () => {
            disposed = true;
        };
    }, [src, streamType, retryVersion]);

    useEffect(() => {
        const video = videoRef.current;
        const rawSource = playbackSource?.trim();
        if (!video || !rawSource || !['hls', 'native'].includes(playableType)) return;

        let hls: Hls | null = null;
        let reconnectTimer: number | undefined;
        let recoveryAttempts = 0;
        let disposed = false;
        const source = resolveVideoStreamUrl(rawSource);

        setStatus('loading');
        setErrorKey(null);

        const markReady = () => {
            if (!disposed) {
                setStatus('ready');
                setErrorKey(null);
            }
        };
        const markError = (key = 'video_stream.playback_error') => {
            if (disposed) return;
            setStatus('error');
            setErrorKey(key);
            if (reconnect && reconnectTimer === undefined) {
                reconnectTimer = window.setTimeout(() => {
                    setRetryVersion((version) => version + 1);
                }, 3000);
            }
        };
        const tryAutoPlay = () => {
            if (autoPlay) void video.play().catch(() => undefined);
        };
        const handleVideoError = () => markError();

        video.addEventListener('loadedmetadata', markReady);
        video.addEventListener('playing', markReady);
        video.addEventListener('error', handleVideoError);

        if (playableType === 'hls') {
            if (video.canPlayType('application/vnd.apple.mpegurl')) {
                video.src = source;
                video.addEventListener('loadedmetadata', tryAutoPlay, { once: true });
            } else if (Hls.isSupported()) {
                hls = new Hls({
                    lowLatencyMode: true,
                    backBufferLength: 30,
                });
                hls.attachMedia(video);
                hls.on(Hls.Events.MEDIA_ATTACHED, () => hls?.loadSource(source));
                hls.on(Hls.Events.MANIFEST_PARSED, tryAutoPlay);
                hls.on(Hls.Events.ERROR, (_event, data) => {
                    if (!data.fatal || !hls) return;
                    if (reconnect && recoveryAttempts < 2 && data.type === ErrorTypes.NETWORK_ERROR) {
                        recoveryAttempts += 1;
                        hls.startLoad();
                        return;
                    }
                    if (reconnect && recoveryAttempts < 2 && data.type === ErrorTypes.MEDIA_ERROR) {
                        recoveryAttempts += 1;
                        hls.recoverMediaError();
                        return;
                    }
                    markError();
                });
            } else {
                markError('video_stream.unsupported_browser');
            }
        } else {
            video.src = source;
            video.load();
            video.addEventListener('loadedmetadata', tryAutoPlay, { once: true });
        }

        return () => {
            disposed = true;
            if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer);
            hls?.destroy();
            video.removeEventListener('loadedmetadata', markReady);
            video.removeEventListener('loadedmetadata', tryAutoPlay);
            video.removeEventListener('playing', markReady);
            video.removeEventListener('error', handleVideoError);
            video.pause();
            video.removeAttribute('src');
            video.load();
        };
    }, [playbackSource, playableType, autoPlay, reconnect, retryVersion]);

    if (!src?.trim()) {
        return (
            <div className={cn('flex aspect-video w-full items-center justify-center rounded-lg border bg-muted/30 text-muted-foreground', className)}>
                <div className="flex flex-col items-center gap-2 text-sm">
                    <VideoOff className="h-8 w-8" />
                    <span>{t('video_stream.empty')}</span>
                </div>
            </div>
        );
    }

    if (['rtmp', 'srt'].includes(streamType)) {
        return (
            <div className={cn('flex aspect-video w-full items-center justify-center rounded-lg border border-amber-500/30 bg-amber-500/5 p-6 text-center', className)}>
                <div className="flex max-w-lg flex-col items-center gap-3 text-sm">
                    <AlertCircle className="h-8 w-8 text-amber-600" />
                    <span>{t('video_stream.unsupported_protocol', { type: streamType.toUpperCase() })}</span>
                </div>
            </div>
        );
    }

    if (streamType === 'rtsp' && !resolvedRtspSource) {
        return (
            <div className={cn('relative flex aspect-video w-full items-center justify-center overflow-hidden rounded-lg border bg-black p-6 text-center text-white', className)}>
                {status === 'error' ? (
                    <div className="flex max-w-lg flex-col items-center gap-3 text-sm">
                        <AlertCircle className="h-7 w-7 text-destructive" />
                        <span>{t(errorKey || 'video_stream.rtsp_gateway_error')}</span>
                        <Button
                            type="button"
                            size="sm"
                            variant="secondary"
                            onClick={() => setRetryVersion((version) => version + 1)}
                        >
                            <RefreshCw className="mr-2 h-4 w-4" />
                            {t('video_stream.retry')}
                        </Button>
                    </div>
                ) : (
                    <div className="flex items-center gap-2 text-sm">
                        <Loader2 className="h-5 w-5 animate-spin" />
                        {t('video_stream.rtsp_converting')}
                    </div>
                )}
            </div>
        );
    }

    return (
        <div className={cn('relative aspect-video w-full overflow-hidden rounded-lg border bg-black', className)}>
            <video
                ref={videoRef}
                className="h-full w-full object-contain"
                poster={poster}
                controls={controls}
                muted={muted}
                autoPlay={autoPlay}
                playsInline
            />
            {status === 'loading' && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/60 text-white">
                    <div className="flex items-center gap-2 text-sm">
                        <Loader2 className="h-5 w-5 animate-spin" />
                        {t('video_stream.loading')}
                    </div>
                </div>
            )}
            {status === 'error' && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/75 p-6 text-center text-white">
                    <div className="flex max-w-lg flex-col items-center gap-3 text-sm">
                        <AlertCircle className="h-7 w-7 text-destructive" />
                        <span>{t(errorKey || 'video_stream.playback_error')}</span>
                        <Button
                            type="button"
                            size="sm"
                            variant="secondary"
                            onClick={() => setRetryVersion((version) => version + 1)}
                        >
                            <RefreshCw className="mr-2 h-4 w-4" />
                            {t('video_stream.retry')}
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
};
