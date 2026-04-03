import * as React from "react"
import { cn } from "../../lib/utils"

export function AvatarFallback({
  name,
  src,
  size = 32,
  className,
  isOnline = false,
}: {
  name?: string
  src?: string | null
  size?: number
  className?: string
  isOnline?: boolean
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
    <div className="relative inline-block" style={{ width: size, height: size }}>
      <div
        className={cn(
          "relative overflow-hidden rounded-full bg-muted flex items-center justify-center text-xs font-semibold text-muted-foreground w-full h-full",
          className
        )}
      >
        {src ? (
          <img src={src} alt={name || "user"} className="h-full w-full object-cover" />
        ) : (
          <span>{initials}</span>
        )}
      </div>
      <span 
        className={cn(
          "absolute bottom-0 right-0 block h-2.5 w-2.5 rounded-full ring-2 ring-background",
          isOnline ? "bg-green-500" : "bg-gray-400"
        )}
        title={isOnline ? "Online" : "Offline"}
      />
    </div>
  )
}

