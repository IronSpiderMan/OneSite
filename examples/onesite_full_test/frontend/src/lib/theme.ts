export type ThemeMode = "system" | "light" | "dark" | "iothub"

const THEME_CLASS_PREFIX = "theme-"
const IOTHUB_CLASS = "theme-iothub"

const getSystemIsDark = () =>
  typeof window !== "undefined" &&
  window.matchMedia &&
  window.matchMedia("(prefers-color-scheme: dark)").matches

const clearThemeClasses = (root: HTMLElement) => {
  const toRemove: string[] = []
  root.classList.forEach((c) => {
    if (c.startsWith(THEME_CLASS_PREFIX)) toRemove.push(c)
  })
  for (const c of toRemove) root.classList.remove(c)
}

export const applyTheme = (mode: ThemeMode) => {
  const root = document.documentElement
  clearThemeClasses(root)

  const effective =
    mode === "system" ? (getSystemIsDark() ? "dark" : "light") : mode

  if (effective === "dark") {
    root.classList.add("dark")
  } else {
    root.classList.remove("dark")
  }

  if (effective === "iothub") {
    root.classList.add("dark")
    root.classList.add(IOTHUB_CLASS)
  }
}

export const getInitialTheme = (): ThemeMode => {
  const raw = localStorage.getItem("custom_config_theme")
  if (raw === "system" || raw === "light" || raw === "dark" || raw === "iothub") return raw
  return "system"
}

export const watchSystemTheme = (onChange: () => void) => {
  const mql = window.matchMedia?.("(prefers-color-scheme: dark)")
  if (!mql) return () => {}

  const handler = () => onChange()
  if (typeof mql.addEventListener === "function") {
    mql.addEventListener("change", handler)
    return () => mql.removeEventListener("change", handler)
  }
  ;(mql as any).addListener(handler)
  return () => (mql as any).removeListener(handler)
}

