import i18n from "../i18n"

export function getUserTimeZone(): string {
  return (
    localStorage.getItem("timezone") ||
    import.meta.env.VITE_TIMEZONE ||
    Intl.DateTimeFormat().resolvedOptions().timeZone ||
    "UTC"
  )
}

function normalizeIsoToJsDateInput(value: string): string {
  const raw = value.trim()

  const hasTz = /([zZ]|[+-]\d{2}:\d{2})$/.test(raw)
  let s = raw

  if (s.includes(".")) {
    const [base, fracAndTz] = s.split(".", 2)
    const m = /^(\d+)(.*)$/.exec(fracAndTz)
    if (m) {
      const frac = m[1].slice(0, 3).padEnd(3, "0")
      const tz = m[2] || ""
      s = `${base}.${frac}${tz}`
    }
  }

  if (!hasTz) s = `${s}Z`
  return s
}

export function formatDateTime(value: unknown, timeZone?: string): string {
  if (value === null || value === undefined) return "-"
  const tz = timeZone || getUserTimeZone()

  const str = String(value).trim()
  if (!str) return "-"

  const normalized = normalizeIsoToJsDateInput(str)
  const d = new Date(normalized)
  if (Number.isNaN(d.getTime())) return str

  try {
    return new Intl.DateTimeFormat(i18n.language || "en", {
      timeZone: tz,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(d)
  } catch {
    return str
  }
}

export function formatTime(value: unknown): string {
  if (value === null || value === undefined) return "-"

  const str = String(value).trim()
  if (!str) return "-"

  // Handle time strings like "14:30:00" or "14:30"
  const timeMatch = str.match(/^(\d{2}):(\d{2})(?::(\d{2}))?$/)
  if (timeMatch) {
    const hours = timeMatch[1]
    const minutes = timeMatch[2]
    return `${hours}:${minutes}`
  }

  // If it's a datetime string, extract time part
  if (str.includes("T")) {
    const timePart = str.split("T")[1]?.split(/[+-]/)[0]
    if (timePart) {
      const parts = timePart.split(":")
      if (parts.length >= 2) {
        return `${parts[0]}:${parts[1]}`
      }
    }
  }

  return str
}
