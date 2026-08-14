import React, { useMemo, useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Badge } from './badge';
import { Button } from './button';
import { Input } from './input';
import {
    detectVideoStreamType,
    VideoStreamPlayer,
    VideoStreamProtocol,
} from './video-stream-player';

interface VideoStreamInputProps {
    value?: string | null;
    onChange: (value: string) => void;
    protocol?: VideoStreamProtocol;
    disabled?: boolean;
}

export const VideoStreamInput: React.FC<VideoStreamInputProps> = ({
    value,
    onChange,
    protocol = 'auto',
    disabled = false,
}) => {
    const { t } = useTranslation();
    const [previewOpen, setPreviewOpen] = useState(false);
    const detectedType = useMemo(
        () => detectVideoStreamType(value || '', protocol),
        [value, protocol],
    );

    return (
        <div className="space-y-3">
            <div className="flex flex-col gap-2 sm:flex-row">
                <Input
                    type="url"
                    value={value || ''}
                    onChange={(event) => onChange(event.target.value)}
                    placeholder={t('video_stream.url_placeholder')}
                    disabled={disabled}
                />
                <Button
                    type="button"
                    variant="outline"
                    onClick={() => setPreviewOpen((open) => !open)}
                    disabled={!value?.trim()}
                    className="shrink-0"
                >
                    {previewOpen ? <EyeOff className="mr-2 h-4 w-4" /> : <Eye className="mr-2 h-4 w-4" />}
                    {t(previewOpen ? 'video_stream.hide_preview' : 'video_stream.preview')}
                </Button>
            </div>
            {value?.trim() && (
                <Badge variant="secondary">
                    {t('video_stream.detected', {
                        type: t(`video_stream.types.${detectedType}`),
                    })}
                </Badge>
            )}
            {previewOpen && value?.trim() && (
                <VideoStreamPlayer
                    src={value}
                    protocol={protocol}
                    autoPlay={false}
                    muted
                    controls
                    reconnect={false}
                    className="max-w-3xl"
                />
            )}
        </div>
    );
};
