import * as React from "react"
import { createPortal } from "react-dom"
import { cn } from "../../lib/utils"
import { X } from "lucide-react"
import { Button } from "./button"

interface ModalProps {
    isOpen: boolean;
    onClose: () => void;
    title: React.ReactNode;
    children: React.ReactNode;
    className?: string;
    footer?: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, className, footer }) => {
    if (!isOpen) return null;

    return createPortal(
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center overflow-y-auto p-4">
            <div className={cn("bg-card text-card-foreground flex max-h-[calc(100dvh-2rem)] w-full max-w-2xl flex-col overflow-hidden border rounded-lg shadow-lg", className)}>
                <div className="flex shrink-0 flex-col space-y-1.5 border-b p-6">
                    <div className="flex items-center justify-between">
                        <h3 className="min-w-0 break-words font-semibold leading-none tracking-tight">{title}</h3>
                        <Button type="button" variant="ghost" size="icon" onClick={onClose} className="h-6 w-6 shrink-0" aria-label="Close">
                            <X className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
                <div className="min-h-0 overflow-y-auto overscroll-contain p-6">
                    {children}
                </div>
                {footer != null && (
                    <div className="shrink-0 border-t bg-card px-6 py-4">{footer}</div>
                )}
            </div>
        </div>,
        document.body
    );
};
