import * as React from 'react'
import { Input } from 'antd'
import { cn } from '../../lib/utils'

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => (
    <Input.TextArea
      ref={ref as any}
      className={cn('w-full', className)}
      autoSize={{ minRows: 4 }}
      {...(props as any)}
    />
  ),
)
Textarea.displayName = 'Textarea'

export { Textarea }
