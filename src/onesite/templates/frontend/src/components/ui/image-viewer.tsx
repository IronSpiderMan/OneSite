import React, { useEffect, useRef, useState } from 'react';
import { Eye, ImageIcon, Loader2, ImageOff, RotateCcw, RotateCw, FlipHorizontal, FlipVertical, ZoomIn, ZoomOut, RefreshCw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from './dialog';
import { Button } from './button';

function ViewerTool({ label, children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
    return (
        <span className="group/tool relative inline-flex">
            <Button type="button" variant="ghost" size="icon" aria-label={label}
                className="h-10 w-10 text-foreground/75 hover:text-foreground aria-pressed:bg-accent aria-pressed:text-accent-foreground" {...props}>
                {children}
            </Button>
            <span aria-hidden="true" className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-popover px-2.5 py-1.5 text-xs text-popover-foreground opacity-0 shadow-md ring-1 ring-border transition-opacity group-hover/tool:opacity-100 group-focus-within/tool:opacity-100 motion-reduce:transition-none">
                {label}
            </span>
        </span>
    );
}

/** Drop-in image thumbnail with an accessible, interactive preview. */
export function ImageViewer({ src, alt = '', className, ...props }: React.ImgHTMLAttributes<HTMLImageElement>) {
    const { i18n } = useTranslation();
    const zh = i18n.language.startsWith('zh');
    const [open, setOpen] = useState(false);
    const [zoom, setZoom] = useState(1);
    const [rotation, setRotation] = useState(0);
    const [flipX, setFlipX] = useState(1);
    const [flipY, setFlipY] = useState(1);
    const [size, setSize] = useState<number | null>(null);
    const [dimensions, setDimensions] = useState('');
    const [failed, setFailed] = useState(false);
    const [loaded, setLoaded] = useState(false);
    const [offset, setOffset] = useState({ x: 0, y: 0 });
    // The dialog mounts through a portal after opening, so track its actual node.
    const [viewport, setViewport] = useState<HTMLDivElement | null>(null);
    const trigger = useRef<HTMLButtonElement>(null);
    const drag = useRef<{ x: number; y: number; left: number; top: number } | null>(null);
    const reset = () => { setZoom(1); setRotation(0); setFlipX(1); setFlipY(1); setOffset({ x: 0, y: 0 }); };
    const changeZoom = (factor: number) => setZoom(value => Math.max(0.1, Math.min(10, value * factor)));

    useEffect(() => {
        if (!open || !src) return;
        reset(); setSize(null); setDimensions(''); setFailed(false); setLoaded(false); drag.current = null;
        const controller = new AbortController();
        // HEAD avoids downloading the image again; unavailable metadata remains explicit.
        fetch(src, { method: 'HEAD', signal: controller.signal }).then(response => {
            const length = response.headers.get('content-length');
            if (response.ok && length && Number.isFinite(Number(length))) setSize(Number(length));
        }).catch(() => {});
        return () => controller.abort();
    }, [open, src]);

    useEffect(() => {
        if (!open || !viewport || !loaded) return;
        const wheel = (event: WheelEvent) => { event.preventDefault(); changeZoom(Math.exp(-event.deltaY * 0.002)); };
        viewport.addEventListener('wheel', wheel, { passive: false });
        return () => viewport.removeEventListener('wheel', wheel);
    }, [open, viewport, loaded]);

    const fileSize = size === null ? (zh ? '大小未知' : 'Size unknown') : size < 1024 ? `${size} B` : size < 1024 ** 2 ? `${(size / 1024).toFixed(1)} KB` : `${(size / 1024 ** 2).toFixed(2)} MB`;
    const transformTools = [
        { label: zh ? '向左旋转' : 'Rotate left', Icon: RotateCcw, run: () => setRotation(v => v - 90) },
        { label: zh ? '向右旋转' : 'Rotate right', Icon: RotateCw, run: () => setRotation(v => v + 90) },
        { label: zh ? '左右翻转' : 'Flip horizontal', Icon: FlipHorizontal, run: () => setFlipX(v => -v), pressed: flipX === -1 },
        { label: zh ? '上下翻转' : 'Flip vertical', Icon: FlipVertical, run: () => setFlipY(v => -v), pressed: flipY === -1 },
    ];
    return (
        <>
            <span className={`group/image-viewer relative block max-w-full ${className || ''}`}>
                <img {...props} src={src} alt={alt} className="block h-full w-full rounded-[inherit] [object-fit:inherit]" />
                {src && <button ref={trigger} type="button" aria-label={zh ? '查看图片' : 'View image'}
                    className="absolute inset-0 flex cursor-zoom-in items-center justify-center rounded-[inherit] bg-black/0 transition-colors hover:bg-black/25 focus-visible:bg-black/25 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
                    onClick={event => { event.stopPropagation(); setOpen(true); }}>
                    <Eye className="h-6 w-6 rounded-full bg-black/60 p-1 text-white opacity-0 transition-opacity group-hover/image-viewer:opacity-100 group-focus-within/image-viewer:opacity-100" />
                </button>}
            </span>
            <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent className="flex h-[88vh] max-h-[960px] w-[calc(100vw-2rem)] max-w-6xl flex-col gap-0 overflow-hidden rounded-lg bg-card p-0 text-card-foreground supports-[height:100dvh]:h-[88dvh] [&>button:last-child]:right-4 [&>button:last-child]:top-5 [&>button:last-child]:flex [&>button:last-child]:h-8 [&>button:last-child]:w-8 [&>button:last-child]:items-center [&>button:last-child]:justify-center [&>button:last-child]:rounded-md [&>button:last-child]:hover:bg-muted"
                    onClick={event => event.stopPropagation()}
                    onCloseAutoFocus={event => { event.preventDefault(); trigger.current?.focus(); }}>
                    <header className="flex shrink-0 items-center gap-3 border-b px-4 py-4 pr-16 sm:px-6 sm:pr-16">
                        <ImageIcon aria-hidden="true" className="hidden h-5 w-5 shrink-0 text-muted-foreground sm:block" />
                        <div className="min-w-0 space-y-1.5">
                            <DialogTitle className="truncate text-base leading-6">{alt || (zh ? '图片预览' : 'Image preview')}</DialogTitle>
                            <DialogDescription className="flex flex-wrap items-center gap-x-2 text-xs leading-5 tabular-nums">
                                <span><span className="sr-only">{zh ? '分辨率' : 'Resolution'}: </span>{dimensions || (zh ? '尺寸未知' : 'Dimensions unknown')}{dimensions && ' px'}</span>
                                <span aria-hidden="true" className="text-border">/</span>
                                <span><span className="sr-only">{zh ? '文件大小' : 'File size'}: </span>{fileSize}</span>
                            </DialogDescription>
                        </div>
                    </header>
                    <div ref={setViewport} aria-busy={!loaded && !failed}
                        className="relative flex min-h-0 flex-1 touch-none items-center justify-center overflow-hidden bg-muted/60 p-4 sm:p-8 cursor-grab active:cursor-grabbing"
                        onDoubleClick={reset}
                        onPointerDown={event => { if (event.button !== 0 || !loaded) return; event.currentTarget.setPointerCapture(event.pointerId); drag.current = { x: event.clientX, y: event.clientY, left: offset.x, top: offset.y }; }}
                        onPointerMove={event => { if (drag.current) setOffset({ x: drag.current.left + event.clientX - drag.current.x, y: drag.current.top + event.clientY - drag.current.y }); }}
                        onPointerUp={() => { drag.current = null; }} onPointerCancel={() => { drag.current = null; }}>
                        {!loaded && !failed && <div role="status" className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-sm text-muted-foreground">
                            <Loader2 aria-hidden="true" className="h-6 w-6 animate-spin motion-reduce:animate-none" />
                            {zh ? '正在加载图片…' : 'Loading image…'}
                        </div>}
                        {failed ? <div role="alert" className="flex flex-col items-center gap-3 text-sm text-muted-foreground">
                            <ImageOff aria-hidden="true" className="h-8 w-8" />
                            <p className="font-medium text-foreground">{zh ? '图片加载失败' : 'Failed to load image'}</p>
                            <p>{zh ? '请关闭预览后重试' : 'Close the preview and try again'}</p>
                        </div> : <img src={src} alt={alt} draggable={false}
                            className={`max-h-full max-w-full flex-none select-none rounded-sm object-contain shadow-sm ${loaded ? 'opacity-100' : 'opacity-0'}`}
                            style={{ transform: `translate(${offset.x}px, ${offset.y}px) scale(${zoom}) scale(${flipX}, ${flipY}) rotate(${rotation}deg)` }}
                            onLoad={event => { setDimensions(`${event.currentTarget.naturalWidth} × ${event.currentTarget.naturalHeight}`); setLoaded(true); }}
                            onError={() => setFailed(true)} />}
                    </div>
                    <footer className="relative flex shrink-0 flex-col items-center gap-2 border-t px-3 py-3 sm:px-5">
                        <div className="flex max-w-full flex-wrap items-center justify-center gap-x-3 gap-y-2 sm:gap-x-4">
                            <div role="group" aria-label={zh ? '旋转与翻转' : 'Rotate and flip'} className="flex w-full items-center justify-center gap-0.5 sm:w-auto">
                                {transformTools.map(({ label, Icon, run, pressed }) => <ViewerTool key={label} label={label} onClick={run} aria-pressed={pressed} disabled={!loaded || failed}>
                                    <Icon aria-hidden="true" className="h-[18px] w-[18px]" strokeWidth={1.75} />
                                </ViewerTool>)}
                            </div>
                            <span aria-hidden="true" className="hidden h-5 w-px bg-border sm:block" />
                            <div role="group" aria-label={zh ? '缩放' : 'Zoom'} className="flex items-center rounded-md bg-muted/70 px-0.5">
                                <ViewerTool label={zh ? '缩小' : 'Zoom out'} onClick={() => changeZoom(1 / 1.2)} disabled={!loaded || failed || zoom <= 0.1}>
                                    <ZoomOut aria-hidden="true" className="h-[18px] w-[18px]" strokeWidth={1.75} />
                                </ViewerTool>
                                <span className="w-14 text-center text-xs font-medium tabular-nums" aria-live="polite" aria-atomic="true">{Math.round(zoom * 100)}%</span>
                                <ViewerTool label={zh ? '放大' : 'Zoom in'} onClick={() => changeZoom(1.2)} disabled={!loaded || failed || zoom >= 10}>
                                    <ZoomIn aria-hidden="true" className="h-[18px] w-[18px]" strokeWidth={1.75} />
                                </ViewerTool>
                            </div>
                            <span aria-hidden="true" className="hidden h-5 w-px bg-border sm:block" />
                            <Button type="button" variant="ghost" size="sm" className="h-10 gap-2 text-foreground/75 hover:text-foreground" onClick={reset} disabled={!loaded || failed}>
                                <RefreshCw aria-hidden="true" className="h-4 w-4" strokeWidth={1.75} />
                                {zh ? '重置' : 'Reset'}
                            </Button>
                        </div>
                        <p className="hidden text-xs leading-5 text-muted-foreground sm:block">{zh ? '滚轮缩放 · 拖拽移动 · 双击重置' : 'Scroll to zoom · Drag to move · Double-click to reset'}</p>
                    </footer>
                </DialogContent>
            </Dialog>
        </>
    );
}
