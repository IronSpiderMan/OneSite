import * as React from "react"
import { Braces, LayoutList, Plus, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Button } from "./button"
import { Input } from "./input"
import { Label } from "./label"
import { Switch } from "./switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./select"
import { JsonInput } from "./json-input"
import { LocationInput } from "./location-input"
import { cn } from "../../lib/utils"

export type JsonFieldSchema = {
  name?: string
  labelKey?: string
  kind: "str" | "int" | "float" | "bool" | "enum" | "datetime" | "model" | "array" | "location" | "any"
  enumValues?: Array<string | number>
  model?: JsonModelSchema
  item?: JsonFieldSchema
}

export type JsonModelSchema = {
  name: string
  fields: JsonFieldSchema[]
}

const EditorModeSwitch: React.FC<{
  mode: "ui" | "json"
  onChange: (mode: "ui" | "json") => void
}> = ({ mode, onChange }) => {
  const { t } = useTranslation()
  return (
    <div className="inline-flex rounded-lg border bg-muted/40 p-1">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className={cn("h-8 gap-1.5 px-3", mode === "ui" && "bg-background shadow-sm hover:bg-background")}
        onClick={() => onChange("ui")}
      >
        <LayoutList className="h-3.5 w-3.5" />
        {t("json_editor.form_mode")}
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className={cn("h-8 gap-1.5 px-3", mode === "json" && "bg-background shadow-sm hover:bg-background")}
        onClick={() => onChange("json")}
      >
        <Braces className="h-3.5 w-3.5" />
        {t("json_editor.source_mode")}
      </Button>
    </div>
  )
}

const buildDefaultValue = (schema: JsonModelSchema) => {
  const obj: Record<string, any> = {}
  for (const f of schema.fields) {
    if (!f.name) continue
    if (f.kind === "bool") obj[f.name] = false
    else if (f.kind === "int") obj[f.name] = 0
    else if (f.kind === "float") obj[f.name] = 0
    else if (f.kind === "enum") obj[f.name] = f.enumValues?.[0]
    else if (f.kind === "model" && f.model) obj[f.name] = buildDefaultValue(f.model)
    else if (f.kind === "array") obj[f.name] = []
    else if (f.kind === "location") obj[f.name] = { latitude: null, longitude: null }
    else obj[f.name] = ""
  }
  return obj
}

const setPathValue = (value: any, path: string[], next: any) => {
  const root = value && typeof value === "object" ? Array.isArray(value) ? [...value] : { ...value } : {}
  let cur: any = root
  for (let i = 0; i < path.length - 1; i++) {
    const key = path[i]
    const existing = cur[key]
    const cloned =
      existing && typeof existing === "object"
        ? Array.isArray(existing)
          ? [...existing]
          : { ...existing }
        : {}
    cur[key] = cloned
    cur = cloned
  }
  cur[path[path.length - 1]] = next
  return root
}

const JsonModelForm: React.FC<{
  schema: JsonModelSchema
  value: any
  onChange: (v: any) => void
  path?: string[]
}> = ({ schema, value, onChange, path = [] }) => {
  const { t } = useTranslation()
  const v = value && typeof value === "object" && !Array.isArray(value) ? value : {}
  return (
    <div className="space-y-4">
      {schema.fields.map((f) => {
        if (!f.name) return null
        const key = f.name
        const fieldPath = [...path, key]
        const cur = v[key]
        if (f.kind === "bool") {
          return (
            <div key={key} className="flex items-center justify-between gap-4 rounded-md border p-3">
              <Label className="font-medium">{t(f.labelKey || key)}</Label>
              <Switch
                checked={Boolean(cur)}
                onCheckedChange={(checked) => onChange(setPathValue(v, fieldPath.slice(path.length), checked))}
              />
            </div>
          )
        }
        if (f.kind === "enum") {
          const stringValue = cur === undefined || cur === null ? "" : String(cur)
          return (
            <div key={key} className="space-y-2">
              <Label>{t(f.labelKey || key)}</Label>
              <Select
                value={stringValue}
                onValueChange={(nv) => onChange(setPathValue(v, fieldPath.slice(path.length), nv))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select" />
                </SelectTrigger>
                <SelectContent>
                  {(f.enumValues ?? []).map((opt) => (
                    <SelectItem key={String(opt)} value={String(opt)}>
                      {String(opt)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )
        }
        if (f.kind === "model" && f.model) {
          return (
            <div key={key} className="space-y-2 rounded-md border p-3">
              <div className="text-sm font-semibold">{t(f.labelKey || key)}</div>
              <JsonModelForm
                schema={f.model}
                value={cur}
                onChange={(nv) => onChange(setPathValue(v, fieldPath.slice(path.length), nv))}
              />
            </div>
          )
        }
        if (f.kind === "location") {
          return (
            <div key={key} className="space-y-2">
              <Label>{t(f.labelKey || key)}</Label>
              <LocationInput
                value={cur}
                onChange={(next) => onChange(setPathValue(v, fieldPath.slice(path.length), next))}
              />
            </div>
          )
        }
        if (f.kind === "array" && f.item) {
          return (
            <div key={key} className="space-y-2 rounded-md border p-3">
              <div className="flex items-center justify-between">
                <div className="text-sm font-semibold">{t(f.labelKey || key)}</div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const arr = Array.isArray(cur) ? [...cur] : []
                    if (f.item?.kind === "model" && f.item.model) arr.push(buildDefaultValue(f.item.model))
                    else arr.push("")
                    onChange(setPathValue(v, fieldPath.slice(path.length), arr))
                  }}
                >
                  <Plus className="mr-1.5 h-3.5 w-3.5" />
                  {t("json_editor.add_item")}
                </Button>
              </div>
              <div className="space-y-3">
                {(Array.isArray(cur) ? cur : []).map((itemVal, idx) => {
                  const itemKey = `${key}-${idx}`
                  const remove = () => {
                    const arr = Array.isArray(cur) ? [...cur] : []
                    arr.splice(idx, 1)
                    onChange(setPathValue(v, fieldPath.slice(path.length), arr))
                  }
                  if (f.item?.kind === "model" && f.item.model) {
                    return (
                      <div key={itemKey} className="rounded-md border p-3">
                        <div className="mb-2 flex items-center justify-between">
                          <div className="text-sm font-medium">{key}[{idx + 1}]</div>
                          <Button type="button" variant="ghost" size="sm" className="text-destructive" onClick={remove}>
                            <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                            {t("common.remove")}
                          </Button>
                        </div>
                        <JsonModelForm
                          schema={f.item.model}
                          value={itemVal}
                          onChange={(nv) => {
                            const arr = Array.isArray(cur) ? [...cur] : []
                            arr[idx] = nv
                            onChange(setPathValue(v, fieldPath.slice(path.length), arr))
                          }}
                        />
                      </div>
                    )
                  }
                  return (
                    <div key={itemKey} className="flex items-center gap-2">
                      <Input
                        value={itemVal ?? ""}
                        onChange={(e) => {
                          const arr = Array.isArray(cur) ? [...cur] : []
                          arr[idx] = e.target.value
                          onChange(setPathValue(v, fieldPath.slice(path.length), arr))
                        }}
                      />
                      <Button type="button" variant="ghost" size="sm" className="text-destructive" onClick={remove}>
                        <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                        {t("common.remove")}
                      </Button>
                    </div>
                  )
                })}
              </div>
            </div>
          )
        }
        const inputType = f.kind === "int" || f.kind === "float" ? "number" : "text"
        return (
          <div key={key} className="space-y-2">
            <Label>{t(f.labelKey || key)}</Label>
            <Input
              type={inputType}
              value={cur ?? ""}
              onChange={(e) => {
                const raw = e.target.value
                const next =
                  f.kind === "int"
                    ? raw === ""
                      ? ""
                      : Number.parseInt(raw, 10)
                    : f.kind === "float"
                      ? raw === ""
                        ? ""
                        : Number.parseFloat(raw)
                      : raw
                onChange(setPathValue(v, fieldPath.slice(path.length), next))
              }}
            />
          </div>
        )
      })}
    </div>
  )
}

export const JsonModelEditor: React.FC<{
  schema: JsonModelSchema
  value: any
  onChange: (v: any) => void
  className?: string
}> = ({ schema, value, onChange, className }) => {
  const [mode, setMode] = React.useState<"ui" | "json">("ui")
  const objValue = value && typeof value === "object" && !Array.isArray(value) ? value : buildDefaultValue(schema)

  return (
    <div className={cn("space-y-3", className)}>
      <EditorModeSwitch mode={mode} onChange={setMode} />
      {mode === "ui" ? (
        <JsonModelForm schema={schema} value={objValue} onChange={onChange} />
      ) : (
        <JsonInput value={objValue} onChange={onChange} jsonKind="object" />
      )}
    </div>
  )
}

export const JsonModelDictEditor: React.FC<{
  itemSchema: JsonModelSchema
  value: any
  onChange: (v: any) => void
  className?: string
  canAdd?: boolean
  canRemove?: boolean
  fixedKeys?: string[]
  lockKeys?: boolean
}> = ({ itemSchema, value, onChange, className, canAdd = true, canRemove = true, fixedKeys, lockKeys }) => {
  const { t } = useTranslation()
  const [mode, setMode] = React.useState<"ui" | "json">("ui")

  // Lazy-initialize locked keys from current dict value (captured once on first meaningful value)
  const lockedRef = React.useRef<string[] | null>(null)
  const rawValue = value && typeof value === "object" && !Array.isArray(value) ? value : ({} as Record<string, any>)
  if (lockKeys && lockedRef.current === null) {
    const keys = Object.keys(rawValue)
    if (keys.length > 0) lockedRef.current = keys
  }

  const effectiveKeys: string[] | undefined = fixedKeys ?? lockedRef.current ?? undefined
  const isFixed = (effectiveKeys && effectiveKeys.length > 0) || false

  // Ensure value has all keys initialized with defaults when fixed
  const dictValue = React.useMemo(() => {
    const v = rawValue
    if (isFixed && effectiveKeys) {
      const result = { ...v }
      for (const k of effectiveKeys) {
        if (!(k in result)) result[k] = buildDefaultValue(itemSchema)
      }
      return result
    }
    return v
  }, [rawValue, isFixed, effectiveKeys, itemSchema])

  // Convert dict to array for editing
  const toArray = (d: Record<string, any>) =>
    Object.entries(d).map(([key, val]) => ({ __key: key, ...val }))

  // Convert array back to dict (preserves all keys including empty)
  const toDict = (arr: any[]) => {
    const d: Record<string, any> = {}
    for (const item of arr) {
      const { __key, ...rest } = item
      d[__key] = rest
    }
    return d
  }

  const arrValue = toArray(dictValue)

  // Generate a unique temporary key for new entries
  const nextIdRef = React.useRef(0)
  const makeNewKey = () => {
    nextIdRef.current += 1
    return `__new_${nextIdRef.current}`
  }

  return (
    <div className={cn("space-y-3", className)}>
      <EditorModeSwitch mode={mode} onChange={setMode} />
      {mode === "ui" ? (
        <div className="space-y-3">
          {!isFixed && canAdd && (
          <div className="flex items-center justify-end">
            <Button
              type="button"
              size="sm"
              onClick={() => onChange(toDict([...arrValue, { __key: makeNewKey(), ...buildDefaultValue(itemSchema) }]))}
            >
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              {t("json_editor.add_entry")}
            </Button>
          </div>
          )}
          {isFixed
            ? effectiveKeys!.map((key) => {
                const item = dictValue[key] ?? buildDefaultValue(itemSchema)
                return (
                  <div key={key} className="rounded-md border p-3">
                    <div className="mb-2 flex items-center justify-between">
                      <div className="text-sm font-medium">{key}</div>
                    </div>
                    <JsonModelForm
                      schema={itemSchema}
                      value={item}
                      onChange={(nv: any) => {
                        const next = { ...dictValue, [key]: nv }
                        onChange(next)
                      }}
                    />
                  </div>
                )
              })
            : arrValue.map((item, idx) => (
            <div key={idx} className="rounded-md border p-3">
              <div className="mb-2 flex items-center justify-between">
                <div className="text-sm font-medium">{t("json_editor.entry", { index: idx + 1 })}</div>
                {canRemove && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="text-destructive"
                  onClick={() => {
                    const next = [...arrValue]
                    next.splice(idx, 1)
                    onChange(toDict(next))
                  }}
                >
                  <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                  {t("common.remove")}
                </Button>
                )}
              </div>
              <div className="mb-3 space-y-2">
                <Label>{t("json_editor.key")}</Label>
                <Input
                  value={item.__key ?? ""}
                  onChange={(e) => {
                    const next = [...arrValue]
                    next[idx] = { ...next[idx], __key: e.target.value }
                    onChange(toDict(next))
                  }}
                  placeholder={t("json_editor.key_placeholder")}
                />
              </div>
              <JsonModelForm
                schema={itemSchema}
                value={item}
                onChange={(nv: any) => {
                  const next = [...arrValue]
                  next[idx] = { ...nv, __key: next[idx].__key }
                  onChange(toDict(next))
                }}
              />
            </div>
          ))}
        </div>
      ) : (
        <JsonInput value={dictValue} onChange={onChange} jsonKind="object" />
      )}
    </div>
  )
}

export const JsonModelArrayEditor: React.FC<{
  itemSchema: JsonModelSchema
  value: any
  onChange: (v: any) => void
  className?: string
  canAdd?: boolean
  canRemove?: boolean
  showJsonMode?: boolean
}> = ({ itemSchema, value, onChange, className, canAdd = true, canRemove = true, showJsonMode = true }) => {
  const { t } = useTranslation()
  const [mode, setMode] = React.useState<"ui" | "json">("ui")
  const arrValue = Array.isArray(value) ? value : []

  return (
    <div className={cn("space-y-3", className)}>
      {showJsonMode && (
      <EditorModeSwitch mode={mode} onChange={setMode} />
      )}
      {!showJsonMode || mode === "ui" ? (
        <div className="space-y-3">
          {canAdd && (
          <div className="flex items-center justify-end">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onChange([...arrValue, buildDefaultValue(itemSchema)])}
            >
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              {t("json_editor.add_item")}
            </Button>
          </div>
          )}
          {arrValue.map((item, idx) => (
            <div key={idx} className="rounded-md border p-3">
              <div className="mb-2 flex items-center justify-between">
                <div className="text-sm font-medium">{t("json_editor.item", { index: idx + 1 })}</div>
                {canRemove && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="text-destructive"
                  onClick={() => {
                    const next = [...arrValue]
                    next.splice(idx, 1)
                    onChange(next)
                  }}
                >
                  <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                  {t("common.remove")}
                </Button>
                )}
              </div>
              <JsonModelForm
                schema={itemSchema}
                value={item}
                onChange={(nv) => {
                  const next = [...arrValue]
                  next[idx] = nv
                  onChange(next)
                }}
              />
            </div>
          ))}
        </div>
      ) : (
        <JsonInput value={arrValue} onChange={onChange} jsonKind="array" />
      )}
    </div>
  )
}

type ScalarArrayKind = "date" | "datetime" | "time"

const inputTypeForScalarArray = (kind: ScalarArrayKind) =>
  kind === "datetime" ? "datetime-local" : kind

const inputValueForScalarArray = (value: unknown, kind: ScalarArrayKind) => {
  if (value === undefined || value === null) return ""
  const stringValue = String(value)
  // ``datetime-local`` accepts neither a timezone suffix nor seconds by
  // default.  Keep the local wall-clock portion of ISO API values.
  return kind === "datetime" ? stringValue.replace(/Z$/, "").slice(0, 16) : stringValue
}

/** A JSON-array editor for date, datetime, and time scalar values. */
export const JsonScalarArrayEditor: React.FC<{
  itemKind: ScalarArrayKind
  value: any
  onChange: (v: string[]) => void
  className?: string
}> = ({ itemKind, value, onChange, className }) => {
  const { t } = useTranslation()
  const [mode, setMode] = React.useState<"ui" | "json">("ui")
  const arrayValue: string[] = Array.isArray(value) ? value.map((item) => String(item ?? "")) : []

  return (
    <div className={cn("space-y-3", className)}>
      <EditorModeSwitch mode={mode} onChange={setMode} />
      {mode === "ui" ? (
        <div className="space-y-3">
          <div className="flex justify-end">
            <Button type="button" variant="outline" size="sm" onClick={() => onChange([...arrayValue, ""])}>
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              {t("json_editor.add_item")}
            </Button>
          </div>
          {arrayValue.map((item, index) => (
            <div key={index} className="flex items-center gap-2">
              <Input
                type={inputTypeForScalarArray(itemKind)}
                value={inputValueForScalarArray(item, itemKind)}
                onChange={(event) => {
                  const next = [...arrayValue]
                  next[index] = event.target.value
                  onChange(next)
                }}
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="text-destructive"
                onClick={() => onChange(arrayValue.filter((_, itemIndex) => itemIndex !== index))}
              >
                <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                {t("common.remove")}
              </Button>
            </div>
          ))}
        </div>
      ) : (
        <JsonInput value={arrayValue} onChange={onChange} jsonKind="array" />
      )}
    </div>
  )
}
