import * as React from 'react'
import { Switch as AntSwitch } from 'antd'
import { cn } from '../../lib/utils'

export interface SwitchProps {
  checked?: boolean
  defaultChecked?: boolean
  disabled?: boolean
  id?: string
  className?: string
  onCheckedChange?: (checked: boolean) => void
}

const Switch = React.forwardRef<HTMLButtonElement, SwitchProps>(
  ({ className, onCheckedChange, ...props }, ref) => (
    <AntSwitch
      ref={ref as any}
      className={cn(className)}
      onChange={onCheckedChange}
      {...props}
    />
  ),
)
Switch.displayName = 'Switch'

export { Switch }
