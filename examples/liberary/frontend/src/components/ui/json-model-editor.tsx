import * as React from "react"
import { Button } from "./button"
import { Input } from "./input"
import { Label } from "./label"
import { Switch } from "./switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./select"
import { JsonInput } from "./json-input"
import { cn } from "../../lib/utils"

export type JsonFieldSchema = {
  name?: string
  kind: "str" | "int" | "float" | "bool" | "enum" | "datetime" | "model" | "array" | "any"
  enumValues?: Array<string | number>
  model?: JsonModelSchema
  item?: JsonFieldSchema
}

export type JsonModelSchema = {
  name: string
  fields: JsonFieldSchema[]
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
              <Label className="font-medium">{key}</Label>
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
              <Label>{key}</Label>
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
              <div className="text-sm font-semibold">{key}</div>
              <JsonModelForm
                schema={f.model}
                value={cur}
                onChange={(nv) => onChange(setPathValue(v, fieldPath.slice(path.length), nv))}
              />
            </div>
          )
        }
        if (f.kind === "array" && f.item) {
          return (
            <div key={key} className="space-y-2 rounded-md border p-3">
              <div className="flex items-center justify-between">
                <div className="text-sm font-semibold">{key}</div>
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
                  Add
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
                            Remove
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
                        Remove
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
            <Label>{key}</Label>
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
      <div className="flex items-center gap-2">
        <Button type="button" variant={mode === "ui" ? "default" : "outline"} size="sm" onClick={() => setMode("ui")}>
          UI
        </Button>
        <Button
          type="button"
          variant={mode === "json" ? "default" : "outline"}
          size="sm"
          onClick={() => setMode("json")}
        >
          JSON
        </Button>
      </div>
      {mode === "ui" ? (
        <JsonModelForm schema={schema} value={objValue} onChange={onChange} />
      ) : (
        <JsonInput value={objValue} onChange={onChange} jsonKind="object" />
      )}
    </div>
  )
}

export const JsonModelArrayEditor: React.FC<{
  itemSchema: JsonModelSchema
  value: any
  onChange: (v: any) => void
  className?: string
}> = ({ itemSchema, value, onChange, className }) => {
  const [mode, setMode] = React.useState<"ui" | "json">("ui")
  const arrValue = Array.isArray(value) ? value : []

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center gap-2">
        <Button type="button" variant={mode === "ui" ? "default" : "outline"} size="sm" onClick={() => setMode("ui")}>
          UI
        </Button>
        <Button
          type="button"
          variant={mode === "json" ? "default" : "outline"}
          size="sm"
          onClick={() => setMode("json")}
        >
          JSON
        </Button>
      </div>
      {mode === "ui" ? (
        <div className="space-y-3">
          <div className="flex items-center justify-end">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onChange([...arrValue, buildDefaultValue(itemSchema)])}
            >
              Add
            </Button>
          </div>
          {arrValue.map((item, idx) => (
            <div key={idx} className="rounded-md border p-3">
              <div className="mb-2 flex items-center justify-between">
                <div className="text-sm font-medium">Item {idx + 1}</div>
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
                  Remove
                </Button>
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
