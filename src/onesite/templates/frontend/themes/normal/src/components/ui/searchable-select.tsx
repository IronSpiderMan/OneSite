import * as React from 'react'
import { Empty, Select, Spin } from 'antd'

export interface SearchableSelectProps {
  value?: string | number | (string | number)[]
  onValueChange: (value: string | number | (string | number)[]) => void
  onLabelChange?: (label: string) => void
  placeholder?: string
  searchPlaceholder?: string
  emptyText?: string
  loadOptions: (query: string) => Promise<{ label: string; value: string | number; description?: string }[]>
  defaultLabel?: string
  valueLabels?: Record<string, string>
  disabled?: boolean
  optionsKey?: string | number
  multiple?: boolean
}

export function SearchableSelect({
  value,
  onValueChange,
  onLabelChange,
  placeholder = 'Select item...',
  emptyText = 'No item found.',
  loadOptions,
  defaultLabel,
  valueLabels,
  multiple = false,
  disabled = false,
  optionsKey,
}: SearchableSelectProps) {
  const [options, setOptions] = React.useState<{ label: string; value: string | number; description?: string }[]>([])
  const [loading, setLoading] = React.useState(false)
  const requestId = React.useRef(0)
  React.useEffect(() => {
    requestId.current += 1
    setOptions([])
    setLoading(false)
  }, [optionsKey])

  const search = React.useCallback(async (query: string) => {
    const current = ++requestId.current
    setLoading(true)
    try {
      const result = await loadOptions(query)
      if (current === requestId.current) setOptions(result)
    } finally {
      if (current === requestId.current) setLoading(false)
    }
  }, [loadOptions])

  const mergedOptions = React.useMemo(() => {
    const seen = new Set(options.map((option) => String(option.value)))
    const selected = (Array.isArray(value) ? value : value === undefined || value === '' ? [] : [value])
      .filter((item) => !seen.has(String(item)))
      .map((item) => ({ value: item, label: valueLabels?.[String(item)] || defaultLabel || String(item) }))
    return [...selected, ...options]
  }, [defaultLabel, options, value, valueLabels])

  return (
    <Select
      disabled={disabled}
      showSearch
      allowClear
      mode={multiple ? 'multiple' : undefined}
      value={value === '' ? undefined : value as any}
      placeholder={placeholder}
      filterOption={false}
      onOpenChange={(open) => { if (open && options.length === 0) void search('') }}
      onSearch={(query) => void search(query)}
      onChange={(next, option: any) => {
        onValueChange((next ?? (multiple ? [] : '')) as any)
        if (!multiple) onLabelChange?.(String(option?.label || ''))
      }}
      notFoundContent={loading ? <Spin size="small" /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={emptyText} />}
      options={mergedOptions}
      optionRender={(option) => (
        <div>
          <div>{option.data.label}</div>
          {option.data.description && <div className="text-xs text-muted-foreground">{option.data.description}</div>}
        </div>
      )}
      className="w-full"
    />
  )
}
