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
  default?: unknown
  visibleWhen?: Record<string, Array<string | number | boolean | null>>
  requiredWhen?: Record<string, Array<string | number | boolean | null>>
  clearWhenHidden?: boolean
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

export type JsonLayoutNode = {
  kind: "field" | "row" | "section"
  field?: string
  section?: string
  title?: string
  span?: number
  columns?: number
  items?: JsonLayoutNode[]
}

export type JsonModelSchema = {
  name: string
  fields: JsonFieldSchema[]
  layout?: JsonLayoutNode[]
}

const conditionValue = (controller: string, value: Record<string, any>, rootValue?: Record<string, any>) => {
  if (!controller.startsWith("$root.")) return value[controller]
  return controller.slice(6).split(".").reduce<any>((current, part) => current?.[part], rootValue)
}

const matchesCondition = (
  conditions: JsonFieldSchema["visibleWhen"],
  value: Record<string, any>,
  rootValue?: Record<string, any>,
) => {
  if (!conditions) return true
  return Object.entries(conditions).every(([controller, expected]) => {
    const actual = conditionValue(controller, value, rootValue)
    return expected.some((option) => String(option) === String(actual))
  })
}

const normalizeJsonFieldValue = (field: JsonFieldSchema, value: any, rootValue?: Record<string, any>): any => {
  if (field.kind === "model" && field.model) return normalizeJsonModelValue(field.model, value, rootValue)
  if (field.kind === "array" && field.item?.kind === "model" && field.item.model) {
    return Array.isArray(value) ? value.map((item) => normalizeJsonModelValue(field.item!.model!, item, rootValue)) : value
  }
  return value
}

/** Remove stale values from child fields that no longer match their controller. */
const normalizeJsonModelValue = (schema: JsonModelSchema, value: any, rootValue?: Record<string, any>) => {
  const source = value && typeof value === "object" && !Array.isArray(value) ? value : {}
  const result: Record<string, any> = { ...source }
  for (const field of schema.fields) {
    if (!field.name) continue
    if (!matchesCondition(field.visibleWhen, result, rootValue)) {
      if (field.clearWhenHidden) delete result[field.name]
      continue
    }
    if (field.name in result) result[field.name] = normalizeJsonFieldValue(field, result[field.name], rootValue)
  }
  return result
}

const normalizeJsonCollection = (collectionKind: "array" | "dict", schema: JsonModelSchema, value: any, rootValue?: Record<string, any>) => {
  if (collectionKind === "array") {
    return Array.isArray(value) ? value.map((item) => normalizeJsonModelValue(schema, item, rootValue)) : []
  }
  const source = value && typeof value === "object" && !Array.isArray(value) ? value : {}
  return Object.fromEntries(Object.entries(source).map(([key, item]) => [key, normalizeJsonModelValue(schema, item, rootValue)]))
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

const buildDefaultValue = (schema: JsonModelSchema, rootValue?: Record<string, any>) => {
  const obj: Record<string, any> = {}
  for (const f of schema.fields) {
    if (!f.name) continue
    if (!matchesCondition(f.visibleWhen, obj, rootValue)) continue
    if (f.default !== undefined) obj[f.name] = f.default
    else if (f.kind === "bool") obj[f.name] = false
    else if (f.kind === "int") obj[f.name] = 0
    else if (f.kind === "float") obj[f.name] = 0
    else if (f.kind === "foreign_key") obj[f.name] = ""
    else if (f.kind === "enum") obj[f.name] = f.enumValues?.[0]
    else if (f.kind === "model" && f.model) obj[f.name] = buildDefaultValue(f.model, rootValue)
    else if (f.kind === "array") obj[f.name] = []
    else if (f.kind === "location") obj[f.name] = { latitude: null, longitude: null }
    else obj[f.name] = ""
  }
  return normalizeJsonModelValue(schema, obj, rootValue)
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
  layoutDisabled?: boolean
  rootValue?: Record<string, any>
}> = ({ schema, value, onChange, path = [], foreignKeyLoaders, layoutDisabled = false, rootValue }) => {
  const { t } = useTranslation()
  const [collapsedArrayItems, setCollapsedArrayItems] = React.useState<Set<string>>(() => new Set())
  const v = value && typeof value === "object" && !Array.isArray(value) ? value : {}
  const emitChange = (next: any) => onChange(normalizeJsonModelValue(schema, next, rootValue))

  const toggleArrayItem = (itemId: string) => {
    setCollapsedArrayItems((previous) => {
      const next = new Set(previous)
      if (next.has(itemId)) next.delete(itemId)
      else next.add(itemId)
      return next
    })
  }

  const rowClasses: Record<number, string> = {
    1: "grid grid-cols-1 gap-4",
    2: "grid grid-cols-1 gap-4 md:grid-cols-2",
    3: "grid grid-cols-1 gap-4 md:grid-cols-3",
    4: "grid grid-cols-1 gap-4 md:grid-cols-4",
  }
  const spanClasses: Record<number, string> = {
    1: "", 2: "md:col-span-2", 3: "md:col-span-3", 4: "md:col-span-4",
  }
  const renderLayoutNode = (node: JsonLayoutNode, key: string): React.ReactNode => {
    if (node.kind === "field") {
      const field = schema.fields.find((candidate) => candidate.name === node.field)
      if (!field) return null
      return (
        <div key={key} className={`min-w-0 ${spanClasses[node.span ?? 1] || ""}`}>
          <JsonModelForm schema={{ ...schema, fields: [field] }} value={v} onChange={emitChange} path={path} foreignKeyLoaders={foreignKeyLoaders} layoutDisabled rootValue={rootValue} />
        </div>
      )
    }
    const items = (node.items ?? []).map((item, index) => renderLayoutNode(item, `${key}-${index}`)).filter(Boolean)
    if (!items.length) return null
    if (node.kind === "row") return <div key={key} className={rowClasses[node.columns ?? 1] || rowClasses[1]}>{items}</div>
    return (
      <fieldset key={key} className={`min-w-0 rounded-md border p-3 ${spanClasses[node.span ?? 1] || ""}`}>
        <legend className="px-1 text-sm font-semibold">{node.title}</legend>
        <div className="space-y-4">{items}</div>
      </fieldset>
    )
  }

  if (!layoutDisabled && schema.layout?.length) {
    return <div className="space-y-4">{schema.layout.map((node, index) => renderLayoutNode(node, `layout-${index}`))}</div>
  }

  return (
    <div className="space-y-4">
      {schema.fields.map((f) => {
        if (!f.name) return null
        const key = f.name
        if (!matchesCondition(f.visibleWhen, v, rootValue)) return null
        const fieldPath = [...path, key]
        const cur = v[key]
        if (f.kind === "bool") {
          return (
            <div key={key} className="flex items-center justify-between gap-4 rounded-md border p-3">
              <Label className="font-medium">{t(f.labelKey || key)}</Label>
              <Switch
                checked={Boolean(cur)}
                onCheckedChange={(checked) => emitChange(setPathValue(v, fieldPath.slice(path.length), checked))}
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
                onValueChange={(nv) => emitChange(setPathValue(v, fieldPath.slice(path.length), nv))}
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
                onValueChange={(next) => emitChange(setPathValue(v, fieldPath.slice(path.length), next))}
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
                onChange={(nv) => emitChange(setPathValue(v, fieldPath.slice(path.length), nv))}
                foreignKeyLoaders={foreignKeyLoaders}
                rootValue={rootValue}
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
                onChange={(next) => emitChange(setPathValue(v, fieldPath.slice(path.length), next))}
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
                    if (f.item?.kind === "model" && f.item.model) arr.push(buildDefaultValue(f.item.model, rootValue))
                    else arr.push("")
                    emitChange(setPathValue(v, fieldPath.slice(path.length), arr))
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
                    emitChange(setPathValue(v, fieldPath.slice(path.length), arr))
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
                              emitChange(setPathValue(v, fieldPath.slice(path.length), arr))
                            }}
                            foreignKeyLoaders={foreignKeyLoaders}
                            rootValue={rootValue}
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
                          emitChange(setPathValue(v, fieldPath.slice(path.length), arr))
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
                emitChange(setPathValue(v, fieldPath.slice(path.length), next))
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
  rootValue?: Record<string, any>
}> = ({ schema, value, onChange, className, foreignKeyLoaders, rootValue }) => {
  const [mode, setMode] = React.useState<"ui" | "json">("ui")
  const objValue = value && typeof value === "object" && !Array.isArray(value) ? value : buildDefaultValue(schema, rootValue)

  return (
    <div className={cn("space-y-3", className)}>
      <EditorModeSwitch mode={mode} onChange={setMode} />
      {mode === "ui" ? (
        <JsonModelForm schema={schema} value={objValue} onChange={(next) => onChange(normalizeJsonModelValue(schema, next, rootValue))} foreignKeyLoaders={foreignKeyLoaders} rootValue={rootValue} />
      ) : (
      <JsonInput value={objValue} onChange={(next) => onChange(normalizeJsonModelValue(schema, next, rootValue))} jsonKind="object" />
      )}
    </div>
  )
}

/** Read-only renderer for JSON submodels on generated detail pages. */
export const JsonModelDetail: React.FC<{
  schema: JsonModelSchema
  value: any
  className?: string
  rootValue?: Record<string, any>
}> = ({ schema, value, className, rootValue }) => {
  const { t } = useTranslation()
  const data = value && typeof value === "object" && !Array.isArray(value) ? value : {}
  const rowClasses: Record<number, string> = {
    1: "grid grid-cols-1 gap-4",
    2: "grid grid-cols-1 gap-4 md:grid-cols-2",
    3: "grid grid-cols-1 gap-4 md:grid-cols-3",
    4: "grid grid-cols-1 gap-4 md:grid-cols-4",
  }
  const spanClasses: Record<number, string> = {
    1: "", 2: "md:col-span-2", 3: "md:col-span-3", 4: "md:col-span-4",
  }
  const renderField = (field: JsonFieldSchema, key: string): React.ReactNode => {
    if (!field.name || !matchesCondition(field.visibleWhen, data, rootValue)) return null
    const fieldValue = data[field.name]
    let content: React.ReactNode
    if (field.kind === "bool") content = fieldValue ? t("common.yes", "Yes") : t("common.no", "No")
    else if (field.kind === "model" && field.model) content = <JsonModelDetail schema={field.model} value={fieldValue} rootValue={rootValue} />
    else if (field.kind === "array" || (fieldValue && typeof fieldValue === "object")) {
      content = <pre className="max-h-80 overflow-auto overscroll-contain whitespace-pre-wrap break-words rounded-md border bg-muted/40 p-2 text-sm">{JSON.stringify(fieldValue ?? (field.kind === "array" ? [] : {}), null, 2)}</pre>
    } else content = String(fieldValue ?? "-")
    return (
      <div key={key} className="space-y-1">
        <Label className="text-muted-foreground">{t(field.labelKey || field.name)}</Label>
        <div className="font-medium">{content}</div>
      </div>
    )
  }
  const renderLayoutNode = (node: JsonLayoutNode, key: string): React.ReactNode => {
    if (node.kind === "field") {
      const field = schema.fields.find((candidate) => candidate.name === node.field)
      const content = field ? renderField(field, `${key}-field`) : null
      return content ? <div key={key} className={`min-w-0 ${spanClasses[node.span ?? 1] || ""}`}>{content}</div> : null
    }
    const items = (node.items ?? []).map((item, index) => renderLayoutNode(item, `${key}-${index}`)).filter(Boolean)
    if (!items.length) return null
    if (node.kind === "row") return <div key={key} className={rowClasses[node.columns ?? 1] || rowClasses[1]}>{items}</div>
    return (
      <fieldset key={key} className={`min-w-0 rounded-md border p-3 ${spanClasses[node.span ?? 1] || ""}`}>
        <legend className="px-1 text-sm font-semibold">{node.title}</legend>
        <div className="space-y-4">{items}</div>
      </fieldset>
    )
  }

  return (
    <div className={cn("space-y-4", className)}>
      {schema.layout?.length
        ? schema.layout.map((node, index) => renderLayoutNode(node, `detail-layout-${index}`))
        : schema.fields.map((field) => renderField(field, field.name || "field"))}
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
  rootValue?: Record<string, any>
}> = ({ collectionKind, itemSchema, value, onChange, canAdd = true, canRemove = true, fixedKeys, lockKeys = false, rootValue }) => {
  const { t } = useTranslation()
  const arrayValue = Array.isArray(value) ? value : []
  const dictValue = value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, any> : {}
  const keys = fixedKeys ?? Object.keys(dictValue)
  const rows = collectionKind === "array"
    ? arrayValue.map((item, index) => ({ key: String(index), item, index }))
    : keys.map((key, index) => ({ key, item: dictValue[key] ?? buildDefaultValue(itemSchema, rootValue), index }))

  const updateItem = (rowIndex: number, next: any) => {
    if (collectionKind === "array") {
      const result = [...arrayValue]
      result[rowIndex] = normalizeJsonModelValue(itemSchema, next, rootValue)
      onChange(result)
    } else {
      onChange({ ...dictValue, [rows[rowIndex].key]: normalizeJsonModelValue(itemSchema, next, rootValue) })
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
    const next = buildDefaultValue(itemSchema, rootValue)
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
                    {matchesCondition(field.visibleWhen, row.item ?? {}, rootValue) ? (
                      <JsonTableCellEditor
                        field={field}
                        value={field.name ? row.item?.[field.name] : undefined}
                        onChange={(next) => updateItem(rowIndex, field.name ? { ...row.item, [field.name]: next } : row.item)}
                      />
                    ) : <span className="text-muted-foreground">—</span>}
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
  rootValue?: Record<string, any>
}> = ({ itemSchema, value, onChange, className, canAdd = true, canRemove = true, fixedKeys, lockKeys, showJsonMode = true, rootValue }) => {
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
        if (!(k in result)) result[k] = buildDefaultValue(itemSchema, rootValue)
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
              onClick={() => onChange(toDict([...arrValue, { __key: makeNewKey(), ...buildDefaultValue(itemSchema, rootValue) }]))}
            >
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              {t("json_editor.add_entry")}
            </Button>
          </div>
          )}
          {isFixed
            ? effectiveKeys!.map((key) => {
                const item = dictValue[key] ?? buildDefaultValue(itemSchema, rootValue)
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
                      rootValue={rootValue}
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
                  next[idx] = { ...normalizeJsonModelValue(itemSchema, nv, rootValue), __key: next[idx].__key }
                  onChange(toDict(next))
              }}
              rootValue={rootValue}
              />
            </div>
          ))}
        </div>
      ) : (
        <JsonInput value={dictValue} onChange={(next) => onChange(normalizeJsonCollection("dict", itemSchema, next, rootValue))} jsonKind="object" />
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
  rootValue?: Record<string, any>
}> = ({ itemSchema, value, onChange, className, canAdd = true, canRemove = true, showJsonMode = true, foreignKeyLoaders, rootValue }) => {
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
    onChange([...arrValue, buildDefaultValue(itemSchema, rootValue)])
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
                  rootValue={rootValue}
                />
              )}
            </div>
          ))}
        </div>
      ) : (
        <JsonInput value={arrValue} onChange={(next) => onChange(normalizeJsonCollection("array", itemSchema, next, rootValue))} jsonKind="array" />
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
