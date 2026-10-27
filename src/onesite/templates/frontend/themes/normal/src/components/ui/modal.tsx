import * as React from 'react'
import { Modal as AntModal } from 'antd'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title: React.ReactNode
  children: React.ReactNode
  className?: string
  footer?: React.ReactNode
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, className, footer }) => (
  <AntModal
    open={isOpen}
    onCancel={onClose}
    title={title}
    footer={footer ?? null}
    destroyOnHidden
    width={672}
    styles={{ body: { maxHeight: 'calc(100dvh - 16rem)', overflowY: 'auto', overscrollBehavior: 'contain' } }}
    className={className}
  >
    {children}
  </AntModal>
)
