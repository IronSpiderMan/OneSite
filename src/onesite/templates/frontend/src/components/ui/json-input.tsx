import * as React from "react"
import { AlertCircle, Braces, CheckCircle2, Clipboard, List, Wand2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Button } from "./button"
import { Textarea } from "./textarea"
import { cn } from "../../lib/utils"

type JsonKind = "object" | "array"

const MIN_EDITOR_HEIGHT = 120
const MAX_EDITOR_HEIGHT = 384

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

const valueSignature = (value: any) => {
  if (value === undefined || value === null) return "__empty__"
  try {
    return JSON.stringify(value)
  } catch {
    return "__invalid__"
  }
}

const draftSignature = (text: string) => {
  try {
    return valueSignature(parseJson(text))
  } catch {
    return "__invalid__"
  }
}

const errorLocation = (text: string, error: unknown) => {
  const message = error instanceof Error ? error.message : ""
  const match = message.match(/position\s+(\d+)/i)
  if (!match) return null
  const position = Number(match[1])
  const beforeError = text.slice(0, position)
  const lines = beforeError.split("\n")
  return { line: lines.length, column: (lines[lines.length - 1]?.length ?? 0) + 1 }
}

export const JsonInput: React.FC<JsonInputProps> = ({
  value,
  onChange,
  jsonKind = "object",
  className,
  placeholder,
  disabled,
}) => {
  const { t } = useTranslation()
  const textareaRef = React.useRef<HTMLTextAreaElement>(null)
  const focusedRef = React.useRef(false)
  const [text, setText] = React.useState(() => formatJson(value))
  const [error, setError] = React.useState<string | null>(null)
  const [copied, setCopied] = React.useState(false)

  const resizeTextarea = React.useCallback(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    textarea.style.height = "auto"
    const nextHeight = Math.min(
      Math.max(textarea.scrollHeight, MIN_EDITOR_HEIGHT),
      MAX_EDITOR_HEIGHT,
    )
    textarea.style.height = `${nextHeight}px`
    textarea.style.overflowY = textarea.scrollHeight > MAX_EDITOR_HEIGHT ? "auto" : "hidden"
  }, [])

  React.useLayoutEffect(() => {
    resizeTextarea()
  }, [text, resizeTextarea])

  React.useEffect(() => {
    window.addEventListener("resize", resizeTextarea)
    return () => window.removeEventListener("resize", resizeTextarea)
  }, [resizeTextarea])

  // Parent form updates are often a response to this editor's own onChange.
  // Preserve the draft in that case so formatting does not move the caret.
  React.useEffect(() => {
    if (focusedRef.current && draftSignature(text) === valueSignature(value)) return
    setText(formatJson(value))
    setError(null)
  }, [value])

  const validateKind = (parsed: any) => {
    if (jsonKind === "array") return Array.isArray(parsed)
    return parsed !== null && typeof parsed === "object" && !Array.isArray(parsed)
  }

  const validateAndEmit = (next: string) => {
    setText(next)
    try {
      const parsed = parseJson(next)
      if (parsed === undefined) {
        setError(null)
        onChange(undefined)
        return true
      }
      if (!validateKind(parsed)) {
        setError(t(`json_editor.${jsonKind}_required`))
        return false
      }
      setError(null)
      onChange(parsed)
      return true
    } catch (parseError) {
      const location = errorLocation(next, parseError)
      setError(
        location
          ? t("json_editor.syntax_error_at", location)
          : t("json_editor.syntax_error"),
      )
      return false
    }
  }

  const formatDraft = () => {
    try {
      const parsed = parseJson(text)
      if (parsed === undefined || !validateKind(parsed)) return
      const formatted = formatJson(parsed)
      setText(formatted)
      setError(null)
    } catch {
      return
    }
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault()
      formatDraft()
      return
    }
    if (event.key !== "Tab") return
    event.preventDefault()
    const target = event.currentTarget
    const start = target.selectionStart
    const end = target.selectionEnd
    const next = `${text.slice(0, start)}  ${text.slice(end)}`
    validateAndEmit(next)
    requestAnimationFrame(() => {
      textareaRef.current?.setSelectionRange(start + 2, start + 2)
    })
  }

  const copyDraft = async () => {
    if (!text || !navigator.clipboard) return
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1200)
    } catch {
      // Clipboard access may be unavailable outside a secure browser context.
    }
  }

  const isEmpty = !text.trim()
  const isValid = !isEmpty && !error
  const Icon = jsonKind === "array" ? List : Braces

  return (
    <div className={cn("overflow-hidden rounded-lg border bg-background", error && "border-destructive/60", className)}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b bg-muted/30 px-3 py-2">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <span>{t(`json_editor.${jsonKind}`)}</span>
          {!isEmpty && (
            <span
              className={cn(
                "inline-flex items-center gap-1 text-xs font-normal",
                error ? "text-destructive" : "text-emerald-600 dark:text-emerald-400",
              )}
            >
              {error ? <AlertCircle className="h-3.5 w-3.5" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
              {error ? t("json_editor.invalid") : t("json_editor.valid")}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-8 gap-1.5 px-2 text-xs"
            onClick={formatDraft}
            disabled={disabled || !isValid}
            title={t("json_editor.format_shortcut")}
          >
            <Wand2 className="h-3.5 w-3.5" />
            {t("json_editor.format")}
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-8 gap-1.5 px-2 text-xs"
            onClick={copyDraft}
            disabled={disabled || isEmpty}
          >
            <Clipboard className="h-3.5 w-3.5" />
            {copied ? t("json_editor.copied") : t("json_editor.copy")}
          </Button>
        </div>
      </div>
      <Textarea
        ref={textareaRef}
        value={text}
        onChange={(event) => validateAndEmit(event.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => { focusedRef.current = true }}
        onBlur={() => { focusedRef.current = false }}
        placeholder={placeholder}
        disabled={disabled}
        spellCheck={false}
        aria-invalid={Boolean(error)}
        className="min-h-[120px] max-h-96 resize-none overflow-y-auto rounded-none border-0 bg-transparent font-mono text-[13px] leading-6 shadow-none focus-visible:ring-0 focus-visible:ring-offset-0"
      />
      <div className="flex min-h-9 items-center justify-between gap-3 border-t bg-muted/20 px-3 py-1.5 text-xs">
        <div className={cn("flex items-center gap-1.5", error ? "text-destructive" : "text-muted-foreground")}>
          {error ? <AlertCircle className="h-3.5 w-3.5 shrink-0" /> : null}
          <span>{error || (isEmpty ? t("json_editor.empty_hint") : t("json_editor.ready"))}</span>
        </div>
        <span className="hidden shrink-0 text-muted-foreground sm:inline">
          {t("json_editor.line_count", { count: Math.max(1, text.split("\n").length) })}
        </span>
      </div>
    </div>
  )
}
