import * as React from "react"
import { Check, ChevronsUpDown, Loader2 } from "lucide-react"
import { cn } from "../../lib/utils"
import { Button } from "./button"
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
  value?: string | number
  onValueChange: (value: string | number) => void
  placeholder?: string
  searchPlaceholder?: string
  emptyText?: string
  loadOptions: (query: string) => Promise<{ label: string; value: string | number; description?: string }[]>
  defaultLabel?: string
}

export function SearchableSelect({
  value,
  onValueChange,
  placeholder = "Select item...",
  searchPlaceholder = "Search...",
  emptyText = "No item found.",
  loadOptions,
  defaultLabel
}: SearchableSelectProps) {
  const [open, setOpen] = React.useState(false)
  const [selectedLabel, setSelectedLabel] = React.useState<string>(defaultLabel || "")
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

  // Update label when value matches an option
  React.useEffect(() => {
    if (value) {
        const found = options.find(o => String(o.value) === String(value))
        if (found) {
            setSelectedLabel(found.label)
        } else if (!selectedLabel && defaultLabel) {
            // Keep default label if available and option not found yet (e.g. initial load)
            setSelectedLabel(defaultLabel)
        }
    } else {
        setSelectedLabel("")
    }
  }, [value, options, defaultLabel])

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between font-normal"
        >
          {selectedLabel || placeholder}
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
            {options.map((option) => (
              <CommandItem
                key={option.value}
                value={String(option.value)}
                onSelect={(currentValue) => {
                  // value is the stringified option.value
                  // We need to pass back the original value type if possible, but CommandItem only supports string value
                  // Here we find the original option
                  const opt = options.find(o => String(o.value) === currentValue)
                  if (opt) {
                      onValueChange(opt.value)
                      setSelectedLabel(opt.label)
                  }
                  setOpen(false)
                }}
              >
                <Check
                  className={cn(
                    "mr-2 h-4 w-4",
                    String(value) === String(option.value) ? "opacity-100" : "opacity-0"
                  )}
                />
                <div className="flex flex-col">
                    <span>{option.label}</span>
                    {option.description && (
                        <span className="text-xs text-muted-foreground">{option.description}</span>
                    )}
                </div>
              </CommandItem>
            ))}
          </CommandGroup>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
