import React, { useState } from 'react';
import { Image, ImagePlus, Loader2, X } from 'lucide-react';
import { Button } from './button';
import { cn } from '../../lib/utils';
import request from '../../utils/request';

interface ImagesUploadProps {
    id?: string;
    value?: string[];
    onChange: (value: string[]) => void;
    className?: string;
}

const toImageUrl = (url: string) => {
    if (!url.startsWith('http') && import.meta.env.VITE_API_URL) {
        const baseUrl = import.meta.env.VITE_API_URL.replace(/\/api\/v1\/?$/, '');
        return `${baseUrl}${url.startsWith('/') ? '' : '/'}${url}`;
    }
    return url;
};

export const ImagesUpload: React.FC<ImagesUploadProps> = ({ id, value = [], onChange, className }) => {
    const [uploading, setUploading] = useState(false);
    const [dragging, setDragging] = useState(false);

    const uploadFiles = async (files: File[]) => {
        if (!files.length) return;

        try {
            setUploading(true);
            const uploaded = await Promise.all(files.map(async (file) => {
                const formData = new FormData();
                formData.append('file', file);
                const response = await request.post('/upload', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' },
                });
                return toImageUrl(response.data.url);
            }));
            onChange([...value, ...uploaded]);
        } catch (error) {
            console.error('Upload failed:', error);
            alert('Upload failed. Please try again.');
        } finally {
            setUploading(false);
        }
    };

    const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(event.target.files || []);
        event.target.value = '';
        await uploadFiles(files);
    };

    const handleDrop = async (event: React.DragEvent<HTMLLabelElement>) => {
        event.preventDefault();
        setDragging(false);
        await uploadFiles(Array.from(event.dataTransfer.files).filter((file) => file.type.startsWith('image/')));
    };

    const removeImage = (index: number) => onChange(value.filter((_, itemIndex) => itemIndex !== index));

    return (
        <div className={cn('w-full space-y-4', className)}>
            <label
                htmlFor={id}
                onDragEnter={(event) => {
                    event.preventDefault();
                    setDragging(true);
                }}
                onDragOver={(event) => event.preventDefault()}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                className={cn(
                    'group relative flex min-h-36 cursor-pointer flex-col items-center justify-center overflow-hidden rounded-xl border-2 border-dashed px-6 py-7 text-center transition-all',
                    'border-muted-foreground/25 bg-muted/20 hover:border-primary/50 hover:bg-primary/[0.04]',
                    dragging && 'scale-[1.01] border-primary bg-primary/[0.07] shadow-sm',
                    uploading && 'pointer-events-none cursor-wait opacity-70'
                )}
            >
                <input
                    id={id}
                    type="file"
                    accept="image/*"
                    multiple
                    aria-label="Select images"
                    className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                    onChange={handleUpload}
                    disabled={uploading}
                />
                <div className="pointer-events-none relative z-10 flex flex-col items-center">
                    <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary ring-8 ring-primary/[0.04] transition-transform group-hover:scale-105">
                        {uploading ? <Loader2 className="h-6 w-6 animate-spin" /> : <ImagePlus className="h-6 w-6" />}
                    </div>
                    {uploading ? (
                        <p className="text-sm font-medium">Uploading images...</p>
                    ) : (
                        <>
                            <p className="text-sm font-semibold">Click or drag images here</p>
                            <p className="mt-1 text-xs text-muted-foreground">PNG, JPG, GIF or WebP · Multiple selection supported</p>
                        </>
                    )}
                </div>
            </label>

            {value.length > 0 && (
                <div className="space-y-2.5">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-sm font-medium">
                            <Image className="h-4 w-4 text-muted-foreground" />
                            Uploaded images
                        </div>
                        <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
                            {value.length}
                        </span>
                    </div>
                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                        {value.map((url, index) => (
                            <div key={`${url}-${index}`} className="group/image relative aspect-square overflow-hidden rounded-xl border bg-muted shadow-sm">
                                <img src={url} alt={`Upload ${index + 1}`} className="h-full w-full object-cover transition-transform duration-200 group-hover/image:scale-105" />
                                <div className="absolute inset-0 bg-gradient-to-t from-black/45 via-transparent to-transparent opacity-0 transition-opacity group-hover/image:opacity-100" />
                                <Button
                                    type="button"
                                    variant="destructive"
                                    size="icon"
                                    className="absolute right-2 top-2 h-8 w-8 translate-y-1 opacity-0 shadow-md transition-all group-hover/image:translate-y-0 group-hover/image:opacity-100"
                                    aria-label={`Remove image ${index + 1}`}
                                    onClick={() => removeImage(index)}
                                >
                                    <X className="h-4 w-4" />
                                </Button>
                                <span className="absolute bottom-2 left-2 rounded bg-black/55 px-1.5 py-0.5 text-[10px] font-medium text-white opacity-0 backdrop-blur-sm transition-opacity group-hover/image:opacity-100">
                                    {index + 1}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};
