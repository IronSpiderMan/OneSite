import * as React from "react"
import { Clock } from "lucide-react"
import { cn } from "../../lib/utils"
import { Button } from "./button"
import { Popover, PopoverContent, PopoverTrigger } from "./popover"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./select"

interface TimePickerProps {
  value?: string
  onChange?: (value: string) => void
  placeholder?: string
  disabled?: boolean
  className?: string
}

export function TimePicker({
  value,
  onChange,
  placeholder = "Select time",
  disabled = false,
  className,
}: TimePickerProps) {
  // Parse the initial value
  const parseTime = (timeStr?: string) => {
    if (!timeStr) return { hour: "00", minute: "00" }
    const match = timeStr.match(/^(\d{1,2}):(\d{2})/)
    if (match) {
      return {
        hour: match[1].padStart(2, "0"),
        minute: match[2],
      }
    }
    return { hour: "00", minute: "00" }
  }

  const { hour: initialHour, minute: initialMinute } = parseTime(value)
  const [selectedHour, setSelectedHour] = React.useState(initialHour)
  const [selectedMinute, setSelectedMinute] = React.useState(initialMinute)
  const [open, setOpen] = React.useState(false)

  // Sync internal state with external value
  React.useEffect(() => {
    const { hour, minute } = parseTime(value)
    setSelectedHour(hour)
    setSelectedMinute(minute)
  }, [value])

  const hours = Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, "0"))
  const minutes = Array.from({ length: 60 }, (_, i) => i.toString().padStart(2, "0"))

  const handleHourChange = (newHour: string) => {
    setSelectedHour(newHour)
    onChange?.(`${newHour}:${selectedMinute}`)
  }

  const handleMinuteChange = (newMinute: string) => {
    setSelectedMinute(newMinute)
    onChange?.(`${selectedHour}:${newMinute}`)
  }

  const formatDisplayTime = (time?: string) => {
    if (!time) return null
    const { hour, minute } = parseTime(time)
    const h = parseInt(hour, 10)
    const period = h >= 12 ? "PM" : "AM"
    const displayHour = h % 12 || 12
    return `${displayHour}:${minute} ${period}`
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          disabled={disabled}
          className={cn(
            "w-full justify-start text-left font-normal",
            !value && "text-muted-foreground",
            className
          )}
        >
          <Clock className="mr-2 h-4 w-4" />
          {value ? formatDisplayTime(value) : placeholder}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-4" align="start">
        <div className="flex items-center gap-2">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">Hour</label>
            <Select value={selectedHour} onValueChange={handleHourChange}>
              <SelectTrigger className="w-[70px]">
                <SelectValue placeholder="HH" />
              </SelectTrigger>
              <SelectContent className="max-h-[200px]">
                {hours.map((h) => (
                  <SelectItem key={h} value={h}>
                    {h}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <span className="text-2xl font-bold mt-4">:</span>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">Minute</label>
            <Select value={selectedMinute} onValueChange={handleMinuteChange}>
              <SelectTrigger className="w-[70px]">
                <SelectValue placeholder="MM" />
              </SelectTrigger>
              <SelectContent className="max-h-[200px]">
                {minutes.map((m) => (
                  <SelectItem key={m} value={m}>
                    {m}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="mt-3 flex justify-end">
          <Button
            size="sm"
            onClick={() => setOpen(false)}
          >
            Done
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}
