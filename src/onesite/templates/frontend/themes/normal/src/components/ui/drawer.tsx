import * as React from 'react'
import { Drawer as AntDrawer } from 'antd'

interface DrawerProps {
  isOpen: boolean
  onClose: () => void
  title: React.ReactNode
  children: React.ReactNode
  className?: string
}

export const Drawer: React.FC<DrawerProps> = ({ isOpen, onClose, title, children, className }) => (
  <AntDrawer
    open={isOpen}
    onClose={onClose}
    title={title}
    placement="right"
    width={640}
    className={className}
    destroyOnHidden
  >
    {children}
  </AntDrawer>
)
