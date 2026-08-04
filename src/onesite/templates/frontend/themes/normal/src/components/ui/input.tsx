import * as React from 'react'
import { Input as AntInput } from 'antd'
import { cn } from '../../lib/utils'

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, ...props }, ref) => (
    <AntInput
      ref={ref as any}
      data-ui="input"
      className={cn('w-full', className)}
      {...(props as any)}
    />
  ),
)
Input.displayName = 'Input'

export { Input }
