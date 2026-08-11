export type ThemeStyle = "normal" | "industrial" | "neuron"
export type ThemeMode = "system" | "light" | "dark"

const STYLE_KEY = "theme_style"
const MODE_KEY = "theme_mode"
const LEGACY_KEY = "custom_config_theme"

const ALL_STYLES: ThemeStyle[] = ["normal", "industrial", "neuron"]

const getSystemIsDark = () =>
  typeof window !== "undefined" &&
  window.matchMedia &&
  window.matchMedia("(prefers-color-scheme: dark)").matches

export const applyTheme = (style: ThemeStyle, mode: ThemeMode) => {
  const root = document.documentElement

  // Set data-theme attribute for CSS variable scoping
  root.setAttribute("data-theme", style)

  // Resolve effective mode
  const effectiveDark =
    mode === "system" ? getSystemIsDark() : mode === "dark"

  if (effectiveDark) {
    root.classList.add("dark")
  } else {
    root.classList.remove("dark")
  }
}

export const getInitialStyle = (): ThemeStyle => {
  const raw = localStorage.getItem(STYLE_KEY)
  if (raw && ALL_STYLES.includes(raw as ThemeStyle)) return raw as ThemeStyle
  // Migrate legacy key — if it was "iothub", map to "industrial"
  const legacy = localStorage.getItem(LEGACY_KEY)
  if (legacy === "iothub") return "industrial"
  return "normal"
}

export const getInitialMode = (): ThemeMode => {
  const raw = localStorage.getItem(MODE_KEY)
  if (raw === "light" || raw === "dark" || raw === "system") return raw
  // Migrate legacy key
  const legacy = localStorage.getItem(LEGACY_KEY)
  if (legacy === "light" || legacy === "dark" || legacy === "system") return legacy
  return "system"
}

export const saveTheme = (style: ThemeStyle, mode: ThemeMode) => {
  localStorage.setItem(STYLE_KEY, style)
  localStorage.setItem(MODE_KEY, mode)
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
