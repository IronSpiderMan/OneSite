import * as React from "react"
import { createPortal } from "react-dom"
import { X } from "lucide-react"
import { cn } from "../../lib/utils"
import { Button } from "./button"

interface DrawerProps {
    isOpen: boolean;
    onClose: () => void;
    title: React.ReactNode;
    children: React.ReactNode;
    className?: string;
}

/** A right-side editor panel with the same API as Modal. */
export const Drawer: React.FC<DrawerProps> = ({ isOpen, onClose, title, children, className }) => {
    if (!isOpen) return null;

    return createPortal(
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm" role="presentation" onMouseDown={onClose}>
            <aside
                className={cn("ml-auto flex h-full w-full max-w-2xl flex-col overflow-hidden border-l bg-card text-card-foreground shadow-2xl animate-in slide-in-from-right", className)}
                role="dialog"
                aria-modal="true"
                aria-label={typeof title === "string" ? title : "Editor"}
                onMouseDown={(event) => event.stopPropagation()}
            >
                <div className="flex shrink-0 items-center justify-between border-b p-6">
                    <h3 className="min-w-0 break-words font-semibold leading-none tracking-tight">{title}</h3>
                    <Button type="button" variant="ghost" size="icon" onClick={onClose} className="h-7 w-7 shrink-0" aria-label="Close">
                        <X className="h-4 w-4" />
                    </Button>
                </div>
                <div className="min-h-0 flex-1 overflow-y-auto p-6">{children}</div>
            </aside>
        </div>,
        document.body,
    );
};
