import * as React from 'react'
import { Button as AntButton } from 'antd'
import { cn } from '../../lib/utils'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link'
  size?: 'default' | 'sm' | 'lg' | 'icon'
}

function flattenButtonChildren(children: React.ReactNode): React.ReactNode[] {
  const flattened: React.ReactNode[] = []
  React.Children.forEach(children, (child) => {
    if (React.isValidElement(child) && child.type === React.Fragment) {
      flattened.push(...flattenButtonChildren((child.props as { children?: React.ReactNode }).children))
    } else {
      flattened.push(child)
    }
  })
  return flattened
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', type, children, ...props }, ref) => {
    const antType = variant === 'default' || variant === 'destructive'
      ? 'primary'
      : variant === 'link'
        ? 'link'
        : variant === 'ghost'
          ? 'text'
          : 'default'
    const antSize = size === 'lg' ? 'large' : size === 'sm' ? 'small' : 'middle'
    const flattenedChildren = flattenButtonChildren(children)
    const firstChild = flattenedChildren[0]
    const firstClassName = React.isValidElement(firstChild)
      ? String((firstChild.props as { className?: string }).className || '')
      : ''
    const hasLeadingIcon = React.isValidElement(firstChild) && /(?:^|\s)(?:h|w)-\S+/.test(firstClassName)
    const icon = hasLeadingIcon
      ? React.cloneElement(firstChild as React.ReactElement<any>, {
          className: firstClassName.replace(/(?:^|\s)mr-\S+/g, '').trim(),
        })
      : undefined
    const content = (hasLeadingIcon ? flattenedChildren.slice(1) : flattenedChildren)
      .filter((child) => typeof child !== 'string' || child.trim().length > 0)

    return (
      <AntButton
        ref={ref as any}
        data-ui="button"
        type={antType}
        htmlType={type || 'button'}
        danger={variant === 'destructive'}
        size={antSize}
        icon={icon}
        className={cn(
          'ant-compat-button',
          variant === 'secondary' && 'ant-btn-secondary',
          size === 'icon' && 'ant-btn-icon-only',
          className,
        )}
        {...(props as any)}
      >
        {content}
      </AntButton>
    )
  },
)
Button.displayName = 'Button'

export { Button }
