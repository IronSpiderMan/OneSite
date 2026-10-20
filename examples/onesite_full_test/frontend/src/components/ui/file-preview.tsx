import React, { useEffect, useState } from 'react';
import { Loader2, FileText, AlertCircle } from 'lucide-react';
import mammoth from 'mammoth';
import * as XLSX from 'xlsx';
import Markdown from 'react-markdown';
import request from '../../utils/request';
import axios from 'axios';

interface FilePreviewProps {
    url: string;
}

export const FilePreview: React.FC<FilePreviewProps> = ({ url }) => {
    const [content, setContent] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const ext = url.split('.').pop()?.toLowerCase() || '';

    // Construct full URL for direct access (img, video, audio, iframe) and fetching
    const getFullUrl = (relativeUrl: string) => {
        if (relativeUrl.startsWith('http')) return relativeUrl;
        const apiUrl = import.meta.env.VITE_API_URL;
        if (apiUrl) {
             const baseUrl = apiUrl.replace(/\/api\/v1\/?$/, '');
             return `${baseUrl}${relativeUrl.startsWith('/') ? '' : '/'}${relativeUrl}`;
        }
        return relativeUrl;
    };

    const fullUrl = getFullUrl(url);

    useEffect(() => {
        const fetchContent = async () => {
            // Reset state
            setContent(null);
            setError(null);
            setLoading(true);

            try {
                // Determine fetch type based on extension
                let responseType: 'blob' | 'text' | 'arraybuffer' = 'text';
                if (['docx', 'xlsx', 'pdf', 'mp4', 'mp3'].includes(ext)) {
                    responseType = 'blob';
                }

                // Skip fetching for iframe supported types if we just use the URL
                // Also skip for images as they are handled by <img> tag
                if (['pdf', 'mp4', 'mp3', 'wav', 'ogg', 'webm', 'mov', 'jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'bmp', 'ico', 'tiff', 'tif'].includes(ext)) {
                    setLoading(false);
                    return;
                }

                const response = await axios.get(fullUrl, { responseType });
                
                if (ext === 'docx') {
                    const arrayBuffer = await response.data.arrayBuffer();
                    const result = await mammoth.convertToHtml({ arrayBuffer });
                    setContent(result.value);
                } else if (ext === 'xlsx' || ext === 'xls') {
                     const arrayBuffer = await response.data.arrayBuffer();
                     const workbook = XLSX.read(arrayBuffer);
                     const sheetName = workbook.SheetNames[0];
                     const sheet = workbook.Sheets[sheetName];
                     // Convert to JSON for better rendering control
                     const json = XLSX.utils.sheet_to_json(sheet, { header: 1 });
                     setContent(json);
                } else if (ext === 'csv') {
                     // Parse CSV manually or use XLSX
                     const workbook = XLSX.read(response.data, { type: 'string' });
                     const sheetName = workbook.SheetNames[0];
                     const sheet = workbook.Sheets[sheetName];
                     const json = XLSX.utils.sheet_to_json(sheet, { header: 1 });
                     setContent(json);
                } else if (ext === 'json') {
                    // Try to format JSON
                    try {
                        const json = typeof response.data === 'string' ? JSON.parse(response.data) : response.data;
                        setContent(JSON.stringify(json, null, 2));
                    } catch (e) {
                        setContent(response.data);
                    }
                } else if (['txt', 'py', 'js', 'html', 'css', 'md'].includes(ext)) {
                    setContent(response.data);
                } else {
                    setError('Preview not available for this file type.');
                }

            } catch (err) {
                console.error(err);
                setError('Failed to load file content.');
            } finally {
                setLoading(false);
            }
        };

        if (url) {
            fetchContent();
        }
    }, [url, ext]);

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="mt-2 text-muted-foreground">Loading preview...</p>
            </div>
        );
    }

    // Image
    if (['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'bmp', 'ico', 'tiff', 'tif'].includes(ext)) {
        return (
             <div className="flex justify-center bg-muted/30 rounded-lg p-4">
                <img 
                    src={fullUrl} 
                    alt="Preview" 
                    className="max-w-full max-h-[70vh] object-contain rounded-md shadow-sm"
                />
            </div>
        );
    }

    // Video
    if (['mp4', 'webm', 'ogg', 'mov'].includes(ext)) {
        return (
            <video controls className="w-full max-h-[70vh] rounded-lg shadow-sm bg-black">
                <source src={fullUrl} />
                Your browser does not support the video tag.
            </video>
        );
    }

    // Audio
    if (['mp3', 'wav', 'ogg'].includes(ext)) {
        return (
            <div className="flex items-center justify-center p-8 bg-muted rounded-lg shadow-sm">
                <audio controls className="w-full">
                    <source src={fullUrl} />
                    Your browser does not support the audio tag.
                </audio>
            </div>
        );
    }

    // PDF
    if (ext === 'pdf') {
        return (
            <iframe 
                src={fullUrl} 
                className="w-full h-[75vh] rounded-lg border shadow-sm"
                title="PDF Preview"
            />
        );
    }

    // Word (Docx) - Rendered HTML
    if (ext === 'docx') {
         if (error) return <div className="text-destructive flex items-center gap-2"><AlertCircle size={16}/> {error}</div>;
         return (
            <div 
                className="prose prose-sm max-w-none p-6 bg-white rounded-lg border shadow-sm overflow-auto max-h-[70vh]"
                dangerouslySetInnerHTML={{ __html: content }} 
            />
         );
    }

    // Excel / CSV - Rendered Table
    if (['xlsx', 'xls', 'csv'].includes(ext)) {
         if (error) return <div className="text-destructive flex items-center gap-2"><AlertCircle size={16}/> {error}</div>;
         const data = content as any[][];
         if (!data || data.length === 0) return <div className="text-muted-foreground">Empty file</div>;
         
         return (
            <div className="rounded-lg border shadow-sm overflow-auto max-h-[70vh] bg-white">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b bg-muted/50">
                            {data[0].map((cell, i) => (
                                <th key={i} className="h-10 px-4 text-left align-middle font-medium text-muted-foreground">
                                    {cell}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {data.slice(1).map((row, i) => (
                            <tr key={i} className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                                {row.map((cell, j) => (
                                    <td key={j} className="p-4 align-middle">
                                        {cell}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
         );
    }

    // Markdown
    if (ext === 'md') {
         if (error) return <div className="text-destructive flex items-center gap-2"><AlertCircle size={16}/> {error}</div>;
         return (
             <div className="prose prose-sm max-w-none p-6 bg-white rounded-lg border shadow-sm overflow-auto max-h-[70vh]">
                 <Markdown>{content}</Markdown>
             </div>
         );
    }

    // Text / Code / JSON
    if (['txt', 'py', 'js', 'html', 'css', 'json'].includes(ext)) {
         if (error) return <div className="text-destructive flex items-center gap-2"><AlertCircle size={16}/> {error}</div>;
         return (
            <div className="rounded-lg border shadow-sm overflow-hidden bg-[#1e1e1e] text-[#d4d4d4]">
                <div className="flex items-center px-4 py-2 bg-[#2d2d2d] border-b border-[#3e3e3e] text-xs text-[#9d9d9d]">
                    <FileText className="h-3 w-3 mr-2" />
                    {url.split('/').pop()}
                </div>
                <pre className="p-4 overflow-auto max-h-[70vh] text-sm font-mono whitespace-pre leading-relaxed">
                    {content}
                </pre>
            </div>
         );
    }

    // Default Fallback
    return (
        <div className="flex flex-col items-center justify-center h-64 bg-muted/30 rounded-lg border border-dashed">
            <FileText className="h-12 w-12 text-muted-foreground mb-2" />
            <p className="text-muted-foreground">Preview not available for .{ext} files.</p>
            <p className="text-xs text-muted-foreground mt-1">Please download the file to view it.</p>
        </div>
    );
};
