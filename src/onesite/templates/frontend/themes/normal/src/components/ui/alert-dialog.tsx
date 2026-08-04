import * as React from 'react'
import { Button, Modal } from 'antd'
import { cn } from '../../lib/utils'

interface AlertContextValue { open: boolean; setOpen: (open: boolean) => void }
const AlertContext = React.createContext<AlertContextValue | null>(null)

const AlertDialog: React.FC<{ open?: boolean; onOpenChange?: (open: boolean) => void; children: React.ReactNode }> = ({ open = false, onOpenChange, children }) => (
  <AlertContext.Provider value={{ open, setOpen: (next) => onOpenChange?.(next) }}>{children}</AlertContext.Provider>
)

const AlertDialogTrigger: React.FC<React.PropsWithChildren> = ({ children }) => {
  const context = React.useContext(AlertContext)
  if (!React.isValidElement(children)) return <>{children}</>
  return React.cloneElement(children as React.ReactElement<any>, { onClick: () => context?.setOpen(true) })
}

const AlertDialogPortal: React.FC<React.PropsWithChildren> = ({ children }) => <>{children}</>
const AlertDialogOverlay: React.FC = () => null

const AlertDialogContent: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ className, children }) => {
  const context = React.useContext(AlertContext)
  return (
    <Modal open={!!context?.open} onCancel={() => context?.setOpen(false)} footer={null} destroyOnHidden width={480} className={className}>
      {children}
    </Modal>
  )
}

const AlertDialogHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => <div className={cn('space-y-2', className)} {...props} />
const AlertDialogFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => <div className={cn('mt-6 flex justify-end gap-2', className)} {...props} />
const AlertDialogTitle = ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => <h2 className={cn('text-lg font-semibold', className)} {...props} />
const AlertDialogDescription = ({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => <p className={cn('text-sm text-muted-foreground', className)} {...props} />

const AlertDialogAction = React.forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement>>(
  ({ className, onClick, ...props }, ref) => {
    const context = React.useContext(AlertContext)
    return <Button ref={ref as any} type="primary" danger className={className} onClick={(event) => { onClick?.(event as any); context?.setOpen(false) }} {...(props as any)} />
  },
)
const AlertDialogCancel = React.forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement>>(
  ({ className, onClick, ...props }, ref) => {
    const context = React.useContext(AlertContext)
    return <Button ref={ref as any} className={className} onClick={(event) => { onClick?.(event as any); context?.setOpen(false) }} {...(props as any)} />
  },
)

export {
  AlertDialog,
  AlertDialogTrigger,
  AlertDialogPortal,
  AlertDialogOverlay,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogFooter,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogAction,
  AlertDialogCancel,
}
