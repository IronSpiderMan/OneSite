import * as React from 'react'
import { Tag } from 'antd'
import { cn } from '../../lib/utils'

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline' | null
}

function Badge({ className, variant = 'default', children, ...props }: BadgeProps) {
  const color = variant === 'destructive' ? 'error' : variant === 'secondary' ? 'default' : variant === 'outline' ? undefined : 'blue'
  return <Tag data-ui="badge" color={color} className={cn(className)} {...(props as any)}>{children}</Tag>
}

const badgeVariants = () => ''

export { Badge, badgeVariants }
