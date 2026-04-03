import * as React from "react"
import { GripVertical, X } from "lucide-react"
import { cn } from "../../lib/utils"
import { Badge } from "./badge"
import { SearchableSelect } from "./searchable-select"

type Option = { label: string; value: string | number; description?: string }

export interface LinkTableOrderedSelectProps {
  value?: (string | number)[]
  onValueChange: (value: (string | number)[]) => void
  placeholder?: string
  searchPlaceholder?: string
  emptyText?: string
  loadOptions: (query: string) => Promise<Option[]>
  valueLabels?: Record<string, string>
}

export function LinkTableOrderedSelect({
  value,
  onValueChange,
  placeholder = "Select items...",
  searchPlaceholder = "Search...",
  emptyText = "No item found.",
  loadOptions,
  valueLabels,
}: LinkTableOrderedSelectProps) {
  const ids = Array.isArray(value) ? value : []
  const [addValue, setAddValue] = React.useState<string | number | undefined>(undefined)
  const [localValueLabels, setLocalValueLabels] = React.useState<Record<string, string>>({})
  const dragIndexRef = React.useRef<number | null>(null)

  const items = React.useMemo(() => {
    return ids.map((id) => ({
      id,
      label: valueLabels?.[String(id)] || localValueLabels[String(id)] || String(id),
    }))
  }, [ids, valueLabels, localValueLabels])

  const wrappedLoadOptions = React.useCallback(
    async (query: string) => {
      const opts = await loadOptions(query)
      if (opts?.length) {
        setLocalValueLabels((prev) => {
          const next = { ...prev }
          for (const o of opts) next[String(o.value)] = o.label
          return next
        })
      }
      return opts
    },
    [loadOptions]
  )

  const handleAdd = (v: string | number | (string | number)[]) => {
    if (Array.isArray(v)) return
    setAddValue(undefined)
    if (ids.some((x) => String(x) === String(v))) return
    onValueChange([...ids, v])
  }

  const handleRemove = (e: React.MouseEvent, id: string | number) => {
    e.stopPropagation()
    onValueChange(ids.filter((x) => String(x) !== String(id)))
  }

  const handleDragStart = (e: React.DragEvent<HTMLDivElement>, index: number) => {
    dragIndexRef.current = index
    e.dataTransfer.setData("text/plain", String(index))
    e.dataTransfer.effectAllowed = "move"
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>, dropIndex: number) => {
    e.preventDefault()
    const raw = e.dataTransfer.getData("text/plain")
    const parsed = Number(raw)
    const dragIndex: number | null = Number.isFinite(parsed) ? parsed : dragIndexRef.current
    if (dragIndex === null || dragIndex === dropIndex) return

    const arr = [...ids]
    const [moved] = arr.splice(dragIndex, 1)
    arr.splice(dropIndex, 0, moved)
    onValueChange(arr)
    dragIndexRef.current = null
  }

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = "move"
  }

  return (
    <div className="space-y-2">
      <SearchableSelect
        value={addValue}
        onValueChange={handleAdd}
        placeholder={placeholder}
        searchPlaceholder={searchPlaceholder}
        emptyText={emptyText}
        loadOptions={wrappedLoadOptions}
      />

      {items.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {items.map((it, index) => (
            <Badge
              key={String(it.id)}
              variant="secondary"
              className={cn("mr-1 cursor-move select-none")}
              draggable
              onDragStart={(e) => handleDragStart(e, index)}
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, index)}
            >
              <GripVertical className="mr-1 h-3 w-3 opacity-60" />
              <span className="max-w-[18rem] truncate">{it.label}</span>
              <X
                className="ml-1 h-3 w-3 cursor-pointer text-muted-foreground hover:text-foreground"
                onClick={(e) => handleRemove(e, it.id)}
              />
            </Badge>
          ))}
        </div>
      ) : null}
    </div>
  )
}
