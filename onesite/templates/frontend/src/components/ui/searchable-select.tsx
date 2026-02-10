import * as React from "react"
import { Check, ChevronsUpDown, Loader2, X } from "lucide-react"
import { cn } from "../../lib/utils"
import { Button } from "./button"
import { Badge } from "./badge"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from "./command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "./popover"

export interface SearchableSelectProps {
  value?: string | number | (string | number)[]
  onValueChange: (value: string | number | (string | number)[]) => void
  placeholder?: string
  searchPlaceholder?: string
  emptyText?: string
  loadOptions: (query: string) => Promise<{ label: string; value: string | number; description?: string }[]>
  defaultLabel?: string
  multiple?: boolean
}

export function SearchableSelect({
  value,
  onValueChange,
  placeholder = "Select item...",
  searchPlaceholder = "Search...",
  emptyText = "No item found.",
  loadOptions,
  defaultLabel,
  multiple = false
}: SearchableSelectProps) {
  const [open, setOpen] = React.useState(false)
  const [selectedLabel, setSelectedLabel] = React.useState<string>(defaultLabel || "")
  const [selectedItems, setSelectedItems] = React.useState<{ label: string; value: string | number }[]>([])
  const [options, setOptions] = React.useState<{ label: string; value: string | number; description?: string }[]>([])
  const [loading, setLoading] = React.useState(false)
  
  // Initial load or when opened
  React.useEffect(() => {
    if (open && options.length === 0) {
      handleSearch("")
    }
  }, [open])

  // Handle search with debounce
  const handleSearch = async (query: string) => {
    setLoading(true)
    try {
      const results = await loadOptions(query)
      setOptions(results)
    } catch (error) {
      console.error("Failed to load options:", error)
      setOptions([])
    } finally {
      setLoading(false)
    }
  }

  // Update label/items when value changes
  React.useEffect(() => {
    if (multiple) {
        if (Array.isArray(value) && value.length > 0) {
            // Reconstruct selected items from options if possible
            // Note: If options are not loaded yet, we might miss labels. 
            // In a real app, we might need to fetch selected items by ID.
            // For MVP, we rely on options being populated or just showing ID/unknown if missing.
            const newSelectedItems = (value as (string|number)[]).map(v => {
                const found = options.find(o => String(o.value) === String(v))
                // If we have existing selectedItems, try to find label there too to preserve it
                const existing = selectedItems.find(i => String(i.value) === String(v))
                return {
                    value: v,
                    label: found?.label || existing?.label || String(v)
                }
            })
            // Only update if different length or values to avoid infinite loop
            if (JSON.stringify(newSelectedItems) !== JSON.stringify(selectedItems)) {
                 setSelectedItems(newSelectedItems)
            }
        } else {
            setSelectedItems([])
        }
    } else {
        if (value) {
            const found = options.find(o => String(o.value) === String(value))
            if (found) {
                setSelectedLabel(found.label)
            } else if (!selectedLabel && defaultLabel) {
                setSelectedLabel(defaultLabel)
            }
        } else {
            setSelectedLabel("")
        }
    }
  }, [value, options, defaultLabel, multiple])

  const handleSelect = (optionValue: string | number, optionLabel: string) => {
    if (multiple) {
        const currentValues = Array.isArray(value) ? value : []
        const isSelected = currentValues.some(v => String(v) === String(optionValue))
        let newValues
        if (isSelected) {
            newValues = currentValues.filter(v => String(v) !== String(optionValue))
        } else {
            newValues = [...currentValues, optionValue]
        }
        onValueChange(newValues)
        // Keep open for multiple selection
    } else {
        onValueChange(optionValue)
        setSelectedLabel(optionLabel)
        setOpen(false)
    }
  }

  const handleRemove = (e: React.MouseEvent, itemValue: string | number) => {
      e.stopPropagation()
      if (multiple && Array.isArray(value)) {
          const newValues = value.filter(v => String(v) !== String(itemValue))
          onValueChange(newValues)
      }
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={cn(
            "w-full justify-between font-normal",
            multiple && selectedItems.length > 0 ? "h-auto py-2" : ""
          )}
        >
            {multiple ? (
                selectedItems.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                        {selectedItems.map(item => (
                            <Badge key={item.value} variant="secondary" className="mr-1">
                                {item.label}
                                <X
                                    className="ml-1 h-3 w-3 cursor-pointer text-muted-foreground hover:text-foreground"
                                    onClick={(e) => handleRemove(e, item.value)}
                                />
                            </Badge>
                        ))}
                    </div>
                ) : (
                    placeholder
                )
            ) : (
                selectedLabel || placeholder
            )}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-full p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput 
            placeholder={searchPlaceholder} 
            onValueChange={(val) => handleSearch(val)} 
          />
          <CommandEmpty>
            {loading ? <Loader2 className="h-4 w-4 animate-spin mx-auto" /> : emptyText}
          </CommandEmpty>
          <CommandGroup>
            {options.map((option) => {
                const isSelected = multiple 
                    ? Array.isArray(value) && value.some(v => String(v) === String(option.value))
                    : String(value) === String(option.value)
                
                return (
                  <CommandItem
                    key={option.value}
                    value={String(option.value)}
                    onSelect={() => handleSelect(option.value, option.label)}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        isSelected ? "opacity-100" : "opacity-0"
                      )}
                    />
                    <div className="flex flex-col">
                        <span>{option.label}</span>
                        {option.description && (
                            <span className="text-xs text-muted-foreground">{option.description}</span>
                        )}
                    </div>
                  </CommandItem>
                )
            })}
          </CommandGroup>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
