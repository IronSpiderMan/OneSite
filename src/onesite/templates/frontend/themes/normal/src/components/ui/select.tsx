import * as React from 'react'
import { Select as AntSelect } from 'antd'
import { cn } from '../../lib/utils'

type SelectValueType = string | number

interface SelectProps {
  value?: SelectValueType
  defaultValue?: SelectValueType
  onValueChange?: (value: any) => void
  disabled?: boolean
  children?: React.ReactNode
}

interface MarkerProps {
  children?: React.ReactNode
  className?: string
  value?: SelectValueType
  disabled?: boolean
  placeholder?: React.ReactNode
  id?: string
}

const SelectItem: React.FC<MarkerProps> = () => null
const SelectValue: React.FC<MarkerProps> = () => null
const SelectTrigger = React.forwardRef<HTMLDivElement, MarkerProps>(() => null)
const SelectContent = React.forwardRef<HTMLDivElement, MarkerProps>(() => null)
const SelectGroup: React.FC<MarkerProps> = () => null
const SelectLabel: React.FC<MarkerProps> = () => null
const SelectSeparator: React.FC<MarkerProps> = () => null
const SelectScrollUpButton: React.FC<MarkerProps> = () => null
const SelectScrollDownButton: React.FC<MarkerProps> = () => null

function walk(
  nodes: React.ReactNode,
  result: { options: any[]; trigger?: MarkerProps; placeholder?: React.ReactNode },
) {
  React.Children.forEach(nodes, (node) => {
    if (!React.isValidElement(node)) return
    if (node.type === SelectItem) {
      const props = node.props as MarkerProps
      result.options.push({ value: props.value, label: props.children, disabled: props.disabled })
      return
    }
    if (node.type === SelectTrigger) {
      result.trigger = node.props as MarkerProps
    }
    if (node.type === SelectValue) {
      result.placeholder = (node.props as MarkerProps).placeholder
    }
    walk((node.props as MarkerProps).children, result)
  })
}

const Select: React.FC<SelectProps> = ({ children, onValueChange, ...props }) => {
  const parsed: { options: any[]; trigger?: MarkerProps; placeholder?: React.ReactNode } = { options: [] }
  walk(children, parsed)
  return (
    <AntSelect
      data-ui="select-trigger"
      className={cn('w-full', parsed.trigger?.className)}
      placeholder={parsed.placeholder}
      options={parsed.options}
      onChange={onValueChange}
      {...props}
    />
  )
}

SelectTrigger.displayName = 'SelectTrigger'
SelectContent.displayName = 'SelectContent'

export {
  Select,
  SelectGroup,
  SelectValue,
  SelectTrigger,
  SelectContent,
  SelectLabel,
  SelectItem,
  SelectSeparator,
  SelectScrollUpButton,
  SelectScrollDownButton,
}
