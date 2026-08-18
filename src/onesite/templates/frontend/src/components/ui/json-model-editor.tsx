import * as React from "react"
import { Braces, ChevronDown, ChevronRight, LayoutList, Plus, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Button } from "./button"
import { Input } from "./input"
import { Label } from "./label"
import { Switch } from "./switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./select"
import { JsonInput } from "./json-input"
import { LocationInput } from "./location-input"
import { SearchableSelect } from "./searchable-select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./table"
import { cn } from "../../lib/utils"

export type JsonFieldSchema = {
  name?: string
  labelKey?: string
  kind: "str" | "int" | "float" | "bool" | "enum" | "datetime" | "foreign_key" | "model" | "array" | "location" | "any"
  enumValues?: Array<string | number>
  foreignKey?: {
    targetModel: string
    targetService: string
    labelField: string
  }
  model?: JsonModelSchema
  item?: JsonFieldSchema
}

export type JsonForeignKeyLoaders = Record<string, (query: string) => Promise<{ label: string; value: string | number }[]>>

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
    else if (f.kind === "foreign_key") obj[f.name] = ""
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
  foreignKeyLoaders?: JsonForeignKeyLoaders
}> = ({ schema, value, onChange, path = [], foreignKeyLoaders }) => {
  const { t } = useTranslation()
  const [collapsedArrayItems, setCollapsedArrayItems] = React.useState<Set<string>>(() => new Set())
  const v = value && typeof value === "object" && !Array.isArray(value) ? value : {}

  const toggleArrayItem = (itemId: string) => {
    setCollapsedArrayItems((previous) => {
      const next = new Set(previous)
      if (next.has(itemId)) next.delete(itemId)
      else next.add(itemId)
      return next
    })
  }

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
        if (f.kind === "foreign_key" && foreignKeyLoaders?.[key]) {
          return (
            <div key={key} className="space-y-2">
              <Label>{t(f.labelKey || key)}</Label>
              <SearchableSelect
                value={cur}
                onValueChange={(next) => onChange(setPathValue(v, fieldPath.slice(path.length), next))}
                defaultLabel={cur === undefined || cur === null || cur === "" ? undefined : String(cur)}
                placeholder={`${t("common.select")} ${t(f.labelKey || key)}`}
                searchPlaceholder={`${t("common.search")} ${t(f.labelKey || key)}...`}
                loadOptions={foreignKeyLoaders[key]}
              />
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
                foreignKeyLoaders={foreignKeyLoaders}
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
                    toast.success(t("json_editor.item_added"))
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
                    // Array indexes shift after a removal, so expand the
                    // remaining items instead of collapsing the wrong record.
                    setCollapsedArrayItems(new Set())
                  }
                  if (f.item?.kind === "model" && f.item.model) {
                    return (
                      <div key={itemKey} className="rounded-md border p-3">
                        <div className="mb-2 flex items-center justify-between">
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="h-auto gap-1 px-1.5 py-1 text-sm font-medium hover:bg-muted"
                            onClick={() => toggleArrayItem(itemKey)}
                            aria-expanded={!collapsedArrayItems.has(itemKey)}
                          >
                            {collapsedArrayItems.has(itemKey) ? <ChevronRight className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                            {key}[{idx + 1}]
                          </Button>
                          <Button type="button" variant="ghost" size="sm" className="text-destructive" onClick={remove}>
                            <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                            {t("common.remove")}
                          </Button>
                        </div>
                        {!collapsedArrayItems.has(itemKey) && (
                          <JsonModelForm
                            schema={f.item.model}
                            value={itemVal}
                            onChange={(nv) => {
                              const arr = Array.isArray(cur) ? [...cur] : []
                              arr[idx] = nv
                              onChange(setPathValue(v, fieldPath.slice(path.length), arr))
                            }}
                            foreignKeyLoaders={foreignKeyLoaders}
                          />
                        )}
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
        const inputType = f.kind === "int" || f.kind === "float" || f.kind === "foreign_key" ? "number" : "text"
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
  foreignKeyLoaders?: JsonForeignKeyLoaders
}> = ({ schema, value, onChange, className, foreignKeyLoaders }) => {
  const [mode, setMode] = React.useState<"ui" | "json">("ui")
  const objValue = value && typeof value === "object" && !Array.isArray(value) ? value : buildDefaultValue(schema)

  return (
    <div className={cn("space-y-3", className)}>
      <EditorModeSwitch mode={mode} onChange={setMode} />
      {mode === "ui" ? (
        <JsonModelForm schema={schema} value={objValue} onChange={onChange} foreignKeyLoaders={foreignKeyLoaders} />
      ) : (
        <JsonInput value={objValue} onChange={onChange} jsonKind="object" />
      )}
    </div>
  )
}

const JsonTableCellEditor: React.FC<{
  field: JsonFieldSchema
  value: any
  onChange: (value: any) => void
}> = ({ field, value, onChange }) => {
  if (field.kind === "bool") {
    return <Switch checked={Boolean(value)} onCheckedChange={onChange} />
  }
  if (field.kind === "enum") {
    return (
      <Select value={value == null ? "" : String(value)} onValueChange={onChange}>
        <SelectTrigger className="min-w-[8rem]"><SelectValue /></SelectTrigger>
        <SelectContent>
          {(field.enumValues ?? []).map((option) => (
            <SelectItem key={String(option)} value={String(option)}>{String(option)}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    )
  }
  if (field.kind === "model" || field.kind === "array" || (value !== null && typeof value === "object")) {
    return (
      <JsonInput
        value={value ?? (field.kind === "array" ? [] : {})}
        onChange={onChange}
        jsonKind={field.kind === "array" || Array.isArray(value) ? "array" : "object"}
        className="min-w-[16rem]"
      />
    )
  }
  if (field.kind === "location") {
    return <div className="min-w-[18rem]"><LocationInput value={value} onChange={onChange} /></div>
  }
  const type = field.kind === "int" || field.kind === "float" ? "number" : field.kind === "datetime" ? "datetime-local" : "text"
  return (
    <Input
      type={type}
      className="min-w-[8rem]"
      value={value ?? ""}
      onChange={(event) => {
        const raw = event.target.value
        onChange(field.kind === "int" ? (raw === "" ? "" : Number.parseInt(raw, 10)) : field.kind === "float" ? (raw === "" ? "" : Number.parseFloat(raw)) : raw)
      }}
    />
  )
}

/** Compact inline-table editor used by JSON collection tabs on detail pages. */
export const JsonModelTableEditor: React.FC<{
  collectionKind: "array" | "dict"
  itemSchema: JsonModelSchema
  value: any
  onChange: (value: any) => void
  canAdd?: boolean
  canRemove?: boolean
  fixedKeys?: string[]
  lockKeys?: boolean
}> = ({ collectionKind, itemSchema, value, onChange, canAdd = true, canRemove = true, fixedKeys, lockKeys = false }) => {
  const { t } = useTranslation()
  const arrayValue = Array.isArray(value) ? value : []
  const dictValue = value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, any> : {}
  const keys = fixedKeys ?? Object.keys(dictValue)
  const rows = collectionKind === "array"
    ? arrayValue.map((item, index) => ({ key: String(index), item, index }))
    : keys.map((key, index) => ({ key, item: dictValue[key] ?? buildDefaultValue(itemSchema), index }))

  const updateItem = (rowIndex: number, next: any) => {
    if (collectionKind === "array") {
      const result = [...arrayValue]
      result[rowIndex] = next
      onChange(result)
    } else {
      onChange({ ...dictValue, [rows[rowIndex].key]: next })
    }
  }
  const removeItem = (rowIndex: number) => {
    if (collectionKind === "array") {
      const result = [...arrayValue]
      result.splice(rowIndex, 1)
      onChange(result)
    } else {
      const result = { ...dictValue }
      delete result[rows[rowIndex].key]
      onChange(result)
    }
  }
  const renameKey = (rowIndex: number, nextKey: string) => {
    const oldKey = rows[rowIndex].key
    if (!nextKey || nextKey === oldKey || nextKey in dictValue) return
    const result: Record<string, any> = {}
    for (const [key, item] of Object.entries(dictValue)) result[key === oldKey ? nextKey : key] = item
    onChange(result)
  }
  const addItem = () => {
    const next = buildDefaultValue(itemSchema)
    if (collectionKind === "array") {
      onChange([...arrayValue, next])
      toast.success(t("json_editor.item_added"))
      return
    }
    let index = keys.length + 1
    let key = `item_${index}`
    while (key in dictValue) key = `item_${++index}`
    onChange({ ...dictValue, [key]: next })
  }

  return (
    <div className="space-y-4">
      {canAdd && !(collectionKind === "dict" && (fixedKeys || lockKeys)) && (
        <div className="flex justify-end">
          <Button type="button" variant="outline" size="sm" onClick={addItem}>
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            {t(collectionKind === "dict" ? "json_editor.add_entry" : "json_editor.add_item")}
          </Button>
        </div>
      )}
      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {collectionKind === "dict" && <TableHead className="min-w-[10rem]">{t("json_editor.key")}</TableHead>}
              {itemSchema.fields.map((field) => <TableHead key={field.name}>{t(field.labelKey || field.name || "")}</TableHead>)}
              {canRemove && <TableHead className="w-[5rem]" />}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length ? rows.map((row, rowIndex) => (
              <TableRow key={collectionKind === "dict" ? row.key : rowIndex}>
                {collectionKind === "dict" && (
                  <TableCell>
                    <Input
                      defaultValue={row.key}
                      disabled={Boolean(fixedKeys) || lockKeys}
                      onBlur={(event) => renameKey(rowIndex, event.target.value.trim())}
                    />
                  </TableCell>
                )}
                {itemSchema.fields.map((field) => (
                  <TableCell key={field.name} className="align-top">
                    <JsonTableCellEditor
                      field={field}
                      value={field.name ? row.item?.[field.name] : undefined}
                      onChange={(next) => updateItem(rowIndex, field.name ? { ...row.item, [field.name]: next } : row.item)}
                    />
                  </TableCell>
                ))}
                {canRemove && (
                  <TableCell className="text-right">
                    <Button type="button" variant="ghost" size="icon" className="text-destructive" title={t("common.remove")} onClick={() => removeItem(rowIndex)} disabled={collectionKind === "dict" && (Boolean(fixedKeys) || lockKeys)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                )}
              </TableRow>
            )) : (
              <TableRow><TableCell colSpan={itemSchema.fields.length + (collectionKind === "dict" ? 1 : 0) + (canRemove ? 1 : 0)} className="h-24 text-center">{t("common.no_result")}</TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

/** Table-shaped fallback for untyped List[JSON] and Dict[str, Any]. */
export const JsonDynamicTableEditor: React.FC<{
  collectionKind: "array" | "dict"
  value: any
  onChange: (value: any) => void
}> = ({ collectionKind, value, onChange }) => {
  const { t } = useTranslation()
  const entries: Array<[string, any]> = collectionKind === "array"
    ? (Array.isArray(value) ? value : []).map((item, index) => [String(index), item])
    : Object.entries(value && typeof value === "object" && !Array.isArray(value) ? value : {})

  const emit = (next: Array<[string, any]>) => onChange(collectionKind === "array" ? next.map(([, item]) => item) : Object.fromEntries(next))
  const add = () => {
    if (collectionKind === "array") {
      emit([...entries, [String(entries.length), {}]])
      toast.success(t("json_editor.item_added"))
      return
    }
    let index = entries.length + 1
    let key = `item_${index}`
    const used = new Set(entries.map(([entryKey]) => entryKey))
    while (used.has(key)) key = `item_${++index}`
    emit([...entries, [key, {}]])
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button type="button" variant="outline" size="sm" onClick={add}>
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          {t(collectionKind === "dict" ? "json_editor.add_entry" : "json_editor.add_item")}
        </Button>
      </div>
      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader><TableRow>{collectionKind === "dict" && <TableHead>{t("json_editor.key")}</TableHead>}<TableHead>{t("json_editor.object")}</TableHead><TableHead className="w-[5rem]" /></TableRow></TableHeader>
          <TableBody>
            {entries.length ? entries.map(([key, item], index) => (
              <TableRow key={`${key}-${index}`}>
                {collectionKind === "dict" && <TableCell><Input value={key} onChange={(event) => { const next = [...entries]; next[index] = [event.target.value, item]; emit(next) }} /></TableCell>}
                <TableCell className="min-w-[20rem]">
                  {item !== null && typeof item === "object" ? <JsonInput value={item} onChange={(nextValue) => { const next = [...entries]; next[index] = [key, nextValue]; emit(next) }} jsonKind={Array.isArray(item) ? "array" : "object"} /> : <Input value={item ?? ""} onChange={(event) => { const next = [...entries]; next[index] = [key, event.target.value]; emit(next) }} />}
                </TableCell>
                <TableCell className="text-right"><Button type="button" variant="ghost" size="icon" className="text-destructive" title={t("common.remove")} onClick={() => emit(entries.filter((_, entryIndex) => entryIndex !== index))}><Trash2 className="h-4 w-4" /></Button></TableCell>
              </TableRow>
            )) : <TableRow><TableCell colSpan={collectionKind === "dict" ? 3 : 2} className="h-24 text-center">{t("common.no_result")}</TableCell></TableRow>}
          </TableBody>
        </Table>
      </div>
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
  showJsonMode?: boolean
}> = ({ itemSchema, value, onChange, className, canAdd = true, canRemove = true, fixedKeys, lockKeys, showJsonMode = true }) => {
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
      {showJsonMode && (
      <EditorModeSwitch mode={mode} onChange={setMode} />
      )}
      {!showJsonMode || mode === "ui" ? (
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
  foreignKeyLoaders?: JsonForeignKeyLoaders
}> = ({ itemSchema, value, onChange, className, canAdd = true, canRemove = true, showJsonMode = true, foreignKeyLoaders }) => {
  const { t } = useTranslation()
  const [mode, setMode] = React.useState<"ui" | "json">("ui")
  // Items are expanded by default; retaining only collapsed indexes keeps newly
  // loaded records visible while allowing long inline forms to stay compact.
  const [collapsedIndexes, setCollapsedIndexes] = React.useState<Set<number>>(() => new Set())
  const arrValue = Array.isArray(value) ? value : []

  const toggleItem = (index: number) => {
    setCollapsedIndexes((previous) => {
      const next = new Set(previous)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  const addItem = () => {
    onChange([...arrValue, buildDefaultValue(itemSchema)])
    toast.success(t("json_editor.item_added"))
  }

  const removeItem = (index: number) => {
    const next = [...arrValue]
    next.splice(index, 1)
    onChange(next)
    setCollapsedIndexes((previous) => new Set(
      [...previous]
        .filter((collapsedIndex) => collapsedIndex !== index)
        .map((collapsedIndex) => collapsedIndex > index ? collapsedIndex - 1 : collapsedIndex),
    ))
  }

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
              onClick={addItem}
            >
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              {t("json_editor.add_item")}
            </Button>
          </div>
          )}
          {arrValue.map((item, idx) => (
            <div key={idx} className="rounded-md border p-3">
              <div className="mb-2 flex items-center justify-between">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-auto gap-1 px-1.5 py-1 text-sm font-medium hover:bg-muted"
                  onClick={() => toggleItem(idx)}
                  aria-expanded={!collapsedIndexes.has(idx)}
                >
                  {collapsedIndexes.has(idx) ? <ChevronRight className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  {t("json_editor.item", { index: idx + 1 })}
                </Button>
                {canRemove && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="text-destructive"
                  onClick={() => removeItem(idx)}
                >
                  <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                  {t("common.remove")}
                </Button>
                )}
              </div>
              {!collapsedIndexes.has(idx) && (
                <JsonModelForm
                  schema={itemSchema}
                  value={item}
                  onChange={(nv) => {
                    const next = [...arrValue]
                    next[idx] = nv
                    onChange(next)
                  }}
                  foreignKeyLoaders={foreignKeyLoaders}
                />
              )}
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
            <Button type="button" variant="outline" size="sm" onClick={() => {
              onChange([...arrayValue, ""])
              toast.success(t("json_editor.item_added"))
            }}>
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
