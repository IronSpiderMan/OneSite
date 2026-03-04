import React, { useRef, useState } from 'react';
import { Upload, X, Loader2, Image as ImageIcon } from 'lucide-react';
import { Button } from './button';
import { cn } from '../../lib/utils';
import request from '../../utils/request';

interface ImageUploadProps {
    value?: string;
    onChange: (value: string) => void;
    className?: string;
}

export const ImageUpload: React.FC<ImageUploadProps> = ({
    value,
    onChange,
    className
}) => {
    const inputRef = useRef<HTMLInputElement>(null);
    const [uploading, setUploading] = useState(false);

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        // Reset input value to allow selecting same file again
        if (inputRef.current) {
            inputRef.current.value = '';
        }

        try {
            setUploading(true);
            const formData = new FormData();
            formData.append('file', file);

            // Use the request utility which should handle the base URL
            const response = await request.post('/upload', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            
            // Assuming response returns { url: string }
            // We need to prepend the backend URL if it's a relative path
            // But usually request utils or the backend should handle this. 
            // For now, let's assume the backend returns a relative URL starting with /static
            // and we might need to prepend the API base URL if serving from different port
            // But since we mount static files on the same app, relative path is fine for <img> src
            // IF the frontend and backend are on same domain.
            // If development (Vite 5173 -> FastAPI 8000), we need the full URL.
            
            // Let's rely on the value being a full URL or a path that works.
            // If the backend returns "/static/...", and we are on localhost:5173, 
            // we need localhost:8000/static/...
            
            // A simple hack for development:
            let imageUrl = response.data.url;
            if (!imageUrl.startsWith('http') && import.meta.env.VITE_API_URL) {
                 // Remove /api/v1 if present in VITE_API_URL to get base host
                 // Actually VITE_API_URL usually is http://localhost:8000/api/v1
                 const baseUrl = import.meta.env.VITE_API_URL.replace(/\/api\/v1\/?$/, '');
                 imageUrl = `${baseUrl}${imageUrl.startsWith('/') ? '' : '/'}${imageUrl}`;
            }
            
            onChange(imageUrl);
        } catch (error) {
            console.error('Upload failed:', error);
            alert('Upload failed. Please try again.');
        } finally {
            setUploading(false);
        }
    };

    const handleRemove = () => {
        onChange('');
    };

    return (
        <div className={cn("space-y-4 w-full", className)}>
            {value ? (
                <div className="relative aspect-video w-full max-w-sm overflow-hidden rounded-lg border bg-muted">
                    <img
                        src={value}
                        alt="Upload"
                        className="h-full w-full object-cover"
                    />
                    <div className="absolute right-2 top-2">
                        <Button
                            type="button"
                            variant="destructive"
                            size="icon"
                            onClick={handleRemove}
                        >
                            <X className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
            ) : (
                <div 
                    className="flex aspect-video w-full max-w-sm cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 hover:bg-muted/50 transition-colors"
                    onClick={() => inputRef.current?.click()}
                >
                    {uploading ? (
                        <div className="flex flex-col items-center gap-2 text-muted-foreground">
                            <Loader2 className="h-8 w-8 animate-spin" />
                            <p>Uploading...</p>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center gap-2 text-muted-foreground">
                            <Upload className="h-8 w-8" />
                            <p>Click to upload image</p>
                        </div>
                    )}
                </div>
            )}
            <input
                ref={inputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleUpload}
                disabled={uploading}
            />
        </div>
    );
};
