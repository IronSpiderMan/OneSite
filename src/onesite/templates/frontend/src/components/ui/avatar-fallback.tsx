import * as React from "react"
import { cn } from "../../lib/utils"

export function AvatarFallback({
  name,
  src,
  size = 32,
  className,
}: {
  name?: string
  src?: string | null
  size?: number
  className?: string
}) {
  const initials = React.useMemo(() => {
    const n = String(name || "").trim()
    if (!n) return "U"
    const parts = n.split(/\s+/).filter(Boolean)
    const a = parts[0]?.[0] || "U"
    const b = parts.length > 1 ? parts[parts.length - 1]?.[0] : ""
    return (a + b).toUpperCase()
  }, [name])

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-full bg-muted flex items-center justify-center text-xs font-semibold text-muted-foreground",
        className
      )}
      style={{ width: size, height: size }}
    >
      {src ? (
        <img src={src} alt={name || "user"} className="h-full w-full object-cover" />
      ) : (
        <span>{initials}</span>
      )}
    </div>
  )
}

