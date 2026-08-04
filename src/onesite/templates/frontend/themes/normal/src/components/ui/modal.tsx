import * as React from 'react'
import { Modal as AntModal } from 'antd'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title: React.ReactNode
  children: React.ReactNode
  className?: string
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, className }) => (
  <AntModal
    open={isOpen}
    onCancel={onClose}
    title={title}
    footer={null}
    destroyOnHidden
    width={640}
    className={className}
  >
    {children}
  </AntModal>
)
