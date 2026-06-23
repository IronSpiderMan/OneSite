import * as React from "react"
import { cn } from "../../lib/utils"
import { Textarea } from "./textarea"
import { Button } from "./button"
import Markdown from "react-markdown"

interface MarkdownEditorProps {
  value?: string
  onChange: (value: string) => void
  disabled?: boolean
  placeholder?: string
  minHeight?: number
}

export function MarkdownEditor({
  value = "",
  onChange,
  disabled = false,
  placeholder = "Write markdown here...",
  minHeight = 200,
}: MarkdownEditorProps) {
  const [tab, setTab] = React.useState<"edit" | "preview">("edit")

  return (
    <div className="border rounded-md">
      <div className="flex items-center border-b px-2 gap-1">
        <Button
          type="button"
          variant={tab === "edit" ? "secondary" : "ghost"}
          size="sm"
          className="h-7 text-xs rounded-sm"
          onClick={() => setTab("edit")}
        >
          Edit
        </Button>
        <Button
          type="button"
          variant={tab === "preview" ? "secondary" : "ghost"}
          size="sm"
          className="h-7 text-xs rounded-sm"
          onClick={() => setTab("preview")}
        >
          Preview
        </Button>
      </div>
      {tab === "edit" ? (
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder={placeholder}
          className={cn("border-0 rounded-none focus-visible:ring-0 focus-visible:ring-offset-0")}
          style={{ minHeight }}
        />
      ) : (
        <div
          className="p-4 prose prose-sm max-w-none dark:prose-invert min-h-[200px]"
          style={{ minHeight }}
        >
          {value ? (
            <Markdown>{value}</Markdown>
          ) : (
            <p className="text-muted-foreground text-sm">Nothing to preview</p>
          )}
        </div>
      )}
    </div>
  )
}
