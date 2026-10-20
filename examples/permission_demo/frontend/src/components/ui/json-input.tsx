import * as React from "react"
import { Textarea } from "./textarea"
import { cn } from "../../lib/utils"

type JsonKind = "object" | "array"

export type JsonInputProps = {
  value: any
  onChange: (value: any) => void
  jsonKind?: JsonKind
  className?: string
  placeholder?: string
  disabled?: boolean
}

const formatJson = (value: any) => {
  if (value === undefined || value === null) return ""
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return ""
  }
}

const parseJson = (text: string) => {
  if (!text.trim()) return undefined
  return JSON.parse(text)
}

export const JsonInput: React.FC<JsonInputProps> = ({
  value,
  onChange,
  jsonKind = "object",
  className,
  placeholder,
  disabled,
}) => {
  const [text, setText] = React.useState(() => formatJson(value))
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    setText(formatJson(value))
  }, [value])

  const validateKind = (parsed: any) => {
    if (jsonKind === "array") return Array.isArray(parsed)
    return parsed !== null && typeof parsed === "object" && !Array.isArray(parsed)
  }

  const handleChange = (next: string) => {
    setText(next)
    try {
      const parsed = parseJson(next)
      if (parsed === undefined) {
        setError(null)
        onChange(undefined)
        return
      }
      if (!validateKind(parsed)) {
        setError(jsonKind === "array" ? "JSON 必须是数组" : "JSON 必须是对象")
        return
      }
      setError(null)
      onChange(parsed)
    } catch {
      setError("JSON 格式不正确")
    }
  }

  const handleBlur = () => {
    try {
      const parsed = parseJson(text)
      if (parsed === undefined) return
      if (!validateKind(parsed)) return
      setText(formatJson(parsed))
    } catch {
      return
    }
  }

  return (
    <div className={cn("space-y-2", className)}>
      <Textarea
        value={text}
        onChange={(e) => handleChange(e.target.value)}
        onBlur={handleBlur}
        placeholder={placeholder}
        disabled={disabled}
      />
      {error ? <div className="text-sm text-destructive">{error}</div> : null}
    </div>
  )
}
