import React, { useRef, useState } from 'react';
import { Upload, X, Loader2, File, FileText, FileCode, FileVideo, Music, Eye } from 'lucide-react';
import { Button } from './button';
import { cn } from '../../lib/utils';
import request from '../../utils/request';
import { Modal } from './modal';
import { FilePreview } from './file-preview';

interface FileUploadProps {
    value?: string;
    onChange: (value: string) => void;
    className?: string;
    accept?: string;
    maxSize?: number; // in MB
    readOnly?: boolean;
    allowDownload?: boolean;
}

export const FileUpload: React.FC<FileUploadProps> = ({
    value,
    onChange,
    className,
    accept = "*",
    maxSize = 20, // Default 20MB
    readOnly = false,
    allowDownload = true
}) => {
    const inputRef = useRef<HTMLInputElement>(null);
    const [uploading, setUploading] = useState(false);
    const [previewOpen, setPreviewOpen] = useState(false);

    const getFileIcon = (url: string) => {
        const ext = url.split('.').pop()?.toLowerCase();
        if (['pdf'].includes(ext || '')) return <FileText className="h-10 w-10 text-red-500" />;
        if (['doc', 'docx'].includes(ext || '')) return <FileText className="h-10 w-10 text-blue-500" />;
        if (['xls', 'xlsx', 'csv'].includes(ext || '')) return <FileText className="h-10 w-10 text-green-500" />;
        if (['md', 'txt', 'py', 'js', 'json'].includes(ext || '')) return <FileCode className="h-10 w-10 text-gray-500" />;
        if (['mp4', 'mov', 'avi', 'webm'].includes(ext || '')) return <FileVideo className="h-10 w-10 text-purple-500" />;
        if (['mp3', 'wav'].includes(ext || '')) return <Music className="h-10 w-10 text-yellow-500" />;
        return <File className="h-10 w-10 text-gray-400" />;
    };

    const getFileName = (url: string) => {
        return url.split('/').pop() || 'Unknown File';
    };

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        // Check size
        if (file.size > maxSize * 1024 * 1024) {
            alert(`File size exceeds ${maxSize}MB limit.`);
            return;
        }

        // Reset input value
        if (inputRef.current) {
            inputRef.current.value = '';
        }

        try {
            setUploading(true);
            const formData = new FormData();
            formData.append('file', file);

            const response = await request.post('/upload', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            
            let fileUrl = response.data.url;
            // Handle URL correction similar to ImageUpload
            // If the URL is relative (e.g. /uploads/...), prepend backend URL if in dev mode
            if (!fileUrl.startsWith('http') && import.meta.env.VITE_API_URL) {
                 const baseUrl = import.meta.env.VITE_API_URL.replace(/\/api\/v1\/?$/, '');
                 fileUrl = `${baseUrl}${fileUrl.startsWith('/') ? '' : '/'}${fileUrl}`;
            }
            
            onChange(fileUrl);
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

    const handleDownload = (e: React.MouseEvent) => {
        e.stopPropagation();
        if (value) {
            window.open(value, '_blank');
        }
    };

    return (
        <div className={cn("space-y-4 w-full", className)}>
            {value ? (
                <div className="relative flex items-center p-4 w-full max-w-sm rounded-lg border bg-muted/50 hover:bg-muted transition-colors">
                    <div className="mr-4 flex-shrink-0 cursor-pointer" onClick={() => setPreviewOpen(true)}>
                        {getFileIcon(value)}
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate cursor-pointer hover:underline" 
                           title={getFileName(value)}
                           onClick={() => setPreviewOpen(true)}
                        >
                            {getFileName(value)}
                        </p>
                        <div className="flex gap-2">
                             <Button 
                                variant="link" 
                                className="h-auto p-0 text-xs text-primary"
                                onClick={() => setPreviewOpen(true)}
                            >
                                Preview
                            </Button>
                            {allowDownload && (
                                <>
                                    <span className="text-xs text-muted-foreground">|</span>
                                    <Button 
                                        variant="link" 
                                        className="h-auto p-0 text-xs text-primary"
                                        onClick={handleDownload}
                                    >
                                        Download
                                    </Button>
                                </>
                            )}
                        </div>
                    </div>
                    <div className="ml-2 pointer-events-auto">
                        {!readOnly && (
                            <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 text-muted-foreground hover:text-destructive"
                                onClick={handleRemove}
                            >
                                <X className="h-4 w-4" />
                            </Button>
                        )}
                    </div>
                </div>
            ) : (
                <div 
                    className={cn(
                        "flex h-32 w-full max-w-sm cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 hover:bg-muted/50 transition-colors",
                        readOnly && "cursor-default hover:bg-transparent"
                    )}
                    onClick={() => !readOnly && inputRef.current?.click()}
                >
                    {uploading ? (
                        <div className="flex flex-col items-center gap-2 text-muted-foreground">
                            <Loader2 className="h-8 w-8 animate-spin" />
                            <p>Uploading...</p>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center gap-2 text-muted-foreground">
                            {!readOnly ? (
                                <>
                                    <Upload className="h-8 w-8" />
                                    <p>Click to upload file</p>
                                    <p className="text-xs text-muted-foreground/75">(Max {maxSize}MB)</p>
                                </>
                            ) : (
                                <p>No file attached</p>
                            )}
                        </div>
                    )}
                </div>
            )}
            <input
                ref={inputRef}
                type="file"
                accept={accept}
                className="hidden"
                onChange={handleUpload}
                disabled={uploading}
            />
            
            <Modal
                isOpen={previewOpen}
                onClose={() => setPreviewOpen(false)}
                title={`Preview: ${value ? getFileName(value) : ''}`}
                className="max-w-4xl w-full"
            >
                {value && <FilePreview url={value} />}
            </Modal>
        </div>
    );
};
