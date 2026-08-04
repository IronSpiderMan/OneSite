import * as React from 'react'
import { Divider } from 'antd'

interface SeparatorProps extends React.HTMLAttributes<HTMLDivElement> {
  orientation?: 'horizontal' | 'vertical'
  decorative?: boolean
}

const Separator = React.forwardRef<HTMLDivElement, SeparatorProps>(
  ({ orientation = 'horizontal', decorative: _decorative, ...props }, ref) => (
    <Divider ref={ref as any} type={orientation} {...(props as any)} />
  ),
)
Separator.displayName = 'Separator'

export { Separator }
