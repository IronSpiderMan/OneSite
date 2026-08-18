import * as React from 'react'
import { Input as AntInput } from 'antd'
import { cn } from '../../lib/utils'

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, ...props }, ref) => {
    // Ant Design exposes an InputRef object, while form libraries such as
    // react-hook-form need the native HTMLInputElement to read its value.
    const setInputRef = (instance: { input?: HTMLInputElement | null } | null) => {
      const input = instance?.input ?? null
      if (typeof ref === 'function') {
        ref(input)
      } else if (ref) {
        ref.current = input
      }
    }

    return (
      <AntInput
        ref={setInputRef}
        data-ui="input"
        className={cn('w-full', className)}
        {...(props as any)}
      />
    )
  },
)
Input.displayName = 'Input'

export { Input }
